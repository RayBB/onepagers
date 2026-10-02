// Package main is a lean Go checker that replaces the Python FastAPI server.
//
// It does the same two cheap things the Python server did:
//   1. GET /  -> query Notion for rows missing an AI summary, spawn `python -m
//      worker` as a short-lived subprocess for each batch of up to 10 rows,
//      and return the JSON results. (The heavy stack — litellm, instructor,
//      trafilatura, markitdown — lives only in that subprocess, so this
//      binary stays small.)
//   2. GET /health -> {"status":"ok"}
//
// Idle footprint target: ~10-15 MB (a single static binary, no interpreter).
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"sync"
)

const (
	maxBatch       = 10
	notionBase     = "https://api.notion.com"
	notionVersion  = "2025-09-03"
	workerExe      = "python" // resolved to the venv python via PATH or absolute below
)

// Row is the minimal shape we pass to the worker: {"id","url"}.
type Row struct {
	ID  string `json:"id"`
	URL string `json:"url"`
}

// Result is what the worker writes to stdout per row.
type Result struct {
	ID    string `json:"id"`
	OK    bool   `json:"ok"`
	Error string `json:"error,omitempty"`
}

// failedIDs tracks notion IDs that errored so we don't retry them every
// minute. Lives in-process (a set of strings); resets when the binary restarts.
var (
	failedMu  sync.Mutex
	failedIDs = map[string]struct{}{}
)

var (
	notionToken      = getenv("NOTION_TOKEN")
	notionDatabaseID = getenv("NOTION_DATABASE_ID")
	workerCmd        []string // resolved at startup
	workerDir        string   // dir containing worker.py
)

// getenv reads an env var and strips surrounding quotes, matching the
// behavior of Python's python-dotenv (which Docker's --env-file does not).
func getenv(key string) string {
	v := os.Getenv(key)
	if len(v) >= 2 {
		if (v[0] == '"' && v[len(v)-1] == '"') || (v[0] == '\'' && v[len(v)-1] == '\'') {
			return v[1 : len(v)-1]
		}
	}
	return v
}

// notionClient does one authenticated JSON request to the Notion API.
func notionClient(method, path string, body any) ([]byte, error) {
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, notionBase+path, bodyReader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+notionToken)
	req.Header.Set("Notion-Version", notionVersion)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("notion %s %s: %d: %s", method, path, resp.StatusCode, string(data))
	}
	return data, nil
}

var (
	dataSourceIDOnce sync.Once
	dataSourceID     string
	dataSourceIDErr  error
)

// getDataSourceID fetches and caches the data source id for the database.
// notion-client does the same: GET /v1/databases/{id} -> data_sources[0].id.
func getDataSourceID() (string, error) {
	dataSourceIDOnce.Do(func() {
		path := "/v1/databases/" + notionDatabaseID
		data, err := notionClient(http.MethodGet, path, nil)
		if err != nil {
			dataSourceIDErr = err
			return
		}
		var db struct {
			DataSources []struct {
				ID string `json:"id"`
			} `json:"data_sources"`
		}
		if err := json.Unmarshal(data, &db); err != nil {
			dataSourceIDErr = fmt.Errorf("parse database: %w", err)
			return
		}
		if len(db.DataSources) == 0 {
			dataSourceIDErr = fmt.Errorf("database has no data sources")
			return
		}
		dataSourceID = db.DataSources[0].ID
	})
	return dataSourceID, dataSourceIDErr
}

// queryRowsWithoutAISummary queries the data source for rows missing an AI
// summary and returns their id + url. Mirrors the Python
// get_notion_rows_without_ai_summary exactly: same endpoint, same filter.
func queryRowsWithoutAISummary() ([]Row, error) {
	dsID, err := getDataSourceID()
	if err != nil {
		return nil, fmt.Errorf("get data source id: %w", err)
	}
	body := map[string]any{
		"filter": map[string]any{
			"and": []map[string]any{
				{"property": "A.I. Summary", "rich_text": map[string]bool{"is_empty": true}},
			},
		},
	}
	data, err := notionClient(http.MethodPost, "/v1/data_sources/"+dsID+"/query", body)
	if err != nil {
		return nil, err
	}
	var resp struct {
		Results []struct {
			ID         string `json:"id"`
			Properties struct {
				URL struct {
					URL string `json:"url"`
				} `json:"URL"`
			} `json:"properties"`
		} `json:"results"`
	}
	if err := json.Unmarshal(data, &resp); err != nil {
		return nil, fmt.Errorf("parse query results: %w", err)
	}
	rows := make([]Row, 0, len(resp.Results))
	for _, r := range resp.Results {
		if r.Properties.URL.URL == "" {
			continue
		}
		rows = append(rows, Row{ID: r.ID, URL: r.Properties.URL.URL})
	}
	return rows, nil
}

// runWorkerBatch spawns `python -m worker` with a JSON array of rows on stdin
// and returns the JSON results the worker writes to stdout. One subprocess
// per batch; its memory is reclaimed when it exits.
func runWorkerBatch(rows []Row) []Result {
	payload, _ := json.Marshal(rows)
	cmd := exec.Command(workerCmd[0], workerCmd[1:]...)
	cmd.Dir = workerDir
	cmd.Stdin = bytes.NewReader(payload)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		// If the worker exits non-zero or output is unparseable, fail every
		// row in the batch so the caller records them in failedIDs.
		errMsg := stderr.String()
		if errMsg == "" {
			errMsg = err.Error()
		}
		os.Stderr.Write(stderr.Bytes())
		results := make([]Result, len(rows))
		for i, r := range rows {
			results[i] = Result{ID: r.ID, OK: false, Error: errMsg}
		}
		return results
	}
	var results []Result
	if err := json.Unmarshal(stdout.Bytes(), &results); err != nil {
		errMsg := "unparseable worker output: " + stdout.String()
		if s := stderr.String(); s != "" {
			errMsg = s
		}
		results := make([]Result, len(rows))
		for i, r := range rows {
			results[i] = Result{ID: r.ID, OK: false, Error: errMsg}
		}
		return results
	}
	return results
}

// runAllBatches processes rows in batches of maxBatch, one subprocess at a time.
func runAllBatches(rows []Row) []Result {
	var all []Result
	for i := 0; i < len(rows); i += maxBatch {
		end := i + maxBatch
		if end > len(rows) {
			end = len(rows)
		}
		all = append(all, runWorkerBatch(rows[i:end])...)
	}
	return all
}

// resolveWorker finds the python that runs the worker. We prefer the project's
// venv (if present) so it has litellm/instructor/trafilatura installed.
func resolveWorker() ([]string, string) {
	// /app/.venv/bin/python inside the container, or ./.venv/bin/python locally.
	// The worker dir is /app (container) or . (local) — wherever worker.py lives.
	for _, p := range []string{"/app/.venv/bin/python", "./.venv/bin/python"} {
		if st, err := os.Stat(p); err == nil && !st.IsDir() {
			if p == "/app/.venv/bin/python" {
				return []string{p, "-m", "worker"}, "/app"
			}
			return []string{p, "-m", "worker"}, "."
		}
	}
	// Fall back to whatever python is on PATH; worker.py is in the CWD.
	return []string{workerExe, "-m", "worker"}, "."
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func main() {
	workerCmd, workerDir = resolveWorker()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		rows, err := queryRowsWithoutAISummary()
		if err != nil {
			writeJSON(w, http.StatusOK, map[string]any{"error": err.Error(), "results": []Result{}})
			return
		}
		// Skip ids that have already failed this process lifetime.
		failedMu.Lock()
		var pending []Row
		for _, row := range rows {
			if _, bad := failedIDs[row.ID]; !bad {
				pending = append(pending, row)
			}
		}
		failedMu.Unlock()

		if len(pending) == 0 {
			writeJSON(w, http.StatusOK, map[string]any{"results": []Result{}, "failed": failedKeys()})
			return
		}

		results := runAllBatches(pending)
		failedMu.Lock()
		for _, res := range results {
			if !res.OK {
				failedIDs[res.ID] = struct{}{}
			}
		}
		failedMu.Unlock()
		writeJSON(w, http.StatusOK, map[string]any{"results": results, "failed": failedKeys()})
	})

	port := getenv("PORT")
	if port == "" {
		port = "3000"
	}
	addr := ":" + port
	fmt.Fprintf(os.Stderr, "checker listening on %s (worker: %s)\n", addr, workerCmd)
	srv := &http.Server{Addr: addr, Handler: mux}
	if err := srv.ListenAndServe(); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}

func failedKeys() []string {
	failedMu.Lock()
	defer failedMu.Unlock()
	keys := make([]string, 0, len(failedIDs))
	for k := range failedIDs {
		keys = append(keys, k)
	}
	return keys
}
