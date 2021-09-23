const Counter = {
    data() {
        return {
            authorIdTextBox: '', // this is the value of the box and changes as the box changes
            authorId: 'OL1394244A', // authorID that is currently being searched/shown. The internal representation after go clicked
            status: '',
            authorWorksJson: {},
            authorJson: {},
            includeSubtitles: true, // should subtitles be included in similarity check
            aggressiveNormalization: true,
            settingsVisible: true,
            coversVisible: true,
            authorVisible: true,
            dataToRemember: ['includeSubtitles', 'aggressiveNormalization', 'settingsVisible', 'coversVisible', 'authorVisible', 'searchUntilSimilarity'],
            searchUntilSimilarity: true,
            searchUntilSimilarityDirection: '', // next, previous, random
            // TODO: configurable similarity threshold, disable cache, two columns of settings
            // add count of authors with search results of similar names
        }
    },
    mounted() {
        // Automatically load data if authorId specified in URL
        const queryParams = new URLSearchParams(window.location.search);
        if (queryParams.get("authorId")) {
            this.authorId = queryParams.get("authorId");
        }
    },
    created() {
        for (const dataName of this.dataToRemember) {
            const storedValue = localStorage.getItem(dataName);
            if (storedValue !== null) {
                // we stringify and parse to get boolean values and probably arrays one day too
                this[dataName] = JSON.parse(storedValue);
            }
            this.$watch(dataName, (newVal, oldVal) => {
                localStorage.setItem(dataName, JSON.stringify(newVal));
            })
        }
    },
    watch: {
        async authorId(newValue) {
            this.authorIdTextBox = newValue;
            // set URL
            const url = new URL(window.location);
            url.searchParams.set('authorId', newValue);
            window.history.replaceState(null, '', url.toString());
            this.status = `${this.authorId} - searching`;
            this.getAuthor();
            await this.getAuthorWorks();
            this.findNextSimilarity();
        }
    },
    computed: {
        groupsOfSimilarWorks() {
            const groups = [];
            const similarityThreshold = .9;
            if (!('entries' in this.authorWorksJson)) {
                return []
            }
            // A hack to deep clone
            let entries = JSON.parse(JSON.stringify(this.authorWorksJson.entries));
            console.log("Entry count:", entries.length);
            while (entries.length > 1) {
                const mainWork = entries.shift();
                const similarWorks = this.getSimilarWorksByTitle(mainWork, entries, similarityThreshold);
                if (similarWorks.maxSimilarity > similarityThreshold) {
                    console.log(similarWorks,
                        similarWorks.works.map(work => work.title),
                        similarWorks.works.map(work => work.key.replace("/works/", "")).join(',')
                    );
                    groups.push(similarWorks);
                    entries = entries.filter(entry => !similarWorks.works.includes(entry));
                }
            }
            return groups;
        },
        authorIdNumber() {
            return parseInt(this.authorId.match(/\d+/)[0]);
        },
        authorFieldsToDisplay() {
            const toDisplay = [];
            if (this.authorId) {
                toDisplay.push({
                    "description": "ID",
                    "value": `<a target="_blank" href="https://openlibrary.org/authors/${this.authorId}">${this.authorId}</a>`
                })
            }
            if (this.authorJson?.type?.key === "/type/redirect") {
                toDisplay.push({"description": "Redirect", "value": "True"})
            }
            if (this.authorJson.name) {
                toDisplay.push({"description": "Name", "value": this.authorJson.name})
            }
            if (this.authorJson.name) {
                toDisplay.push({"description": "Works", "value": this.authorWorksJson?.entries?.length || '...'})
            }
            if (this.authorJson.birth_date || this.authorJson.death_date) {
                toDisplay.push({
                    "description": "Lived",
                    "value": `${this.authorJson.birth_date || ''} - ${this.authorJson.death_date || ''}`
                })
            }
            if (this.authorJson?.remote_ids?.wikidata) {
                toDisplay.push({
                    "description": "Wikidata",
                    "value": `<a target="_blank" href="https://www.wikidata.org/wiki/${this.authorJson.remote_ids.wikidata}">${this.authorJson.remote_ids.wikidata}</a>`
                })
            }
            return toDisplay;
        }
    },
    methods: {
        getSimilarWorksByTitle(mainWork, allWorks, similarityThreshold = .9) {
            // main work is the one we want to find similar works to
            const worksExcludingMainWork = allWorks.filter(work => work !== mainWork);
            const titles = worksExcludingMainWork.map(work => this.getTitleFromWork(work).toLowerCase());

            const similarities = stringSimilarity.findBestMatch(this.getTitleFromWork(mainWork).toLowerCase(), titles);
            const similarWorks = similarities.ratings
                .map((result, index) => {
                    if (result.rating > similarityThreshold) {
                        return worksExcludingMainWork[index];
                    }
                })
                .filter(work => work !== undefined);

            similarWorks.push(mainWork);
            return {
                maxSimilarity: similarities.bestMatch.rating,
                works: similarWorks
            }
        },
        getTitleFromWork(work) {
            let title = work.title;
            if (this.includeSubtitles && work.subtitle) {
                title += ` ${work.subtitle}`
            }
            if (this.aggressiveNormalization) {
                title = title.replace(/[^A-Za-z0-9 ]/, '')
                const stopWords = ["the", "and", "at"]; // words to be removed
                for (const word of stopWords) {
                    title = title.replaceAll(` ${word} `, " ")
                }
            }
            return title;
        },
        async goBtnClicked() {
            // TODO: this should grab authorID even from a URL or if there are spaces
            this.searchUntilSimilarityDirection = '';
            // do a refresh if authorId not changed
            if (this.authorId === this.authorIdTextBox) {
                this.getAuthorWorks(false);
            }
            this.authorId = this.authorIdTextBox;
        },
        parseKey(s) {
            return s.split("/")[2];
        },
        getWorkIds(works) {
            return works.map(work => this.parseKey(work.key));
        },
        async fetchWithRetry(url, retries = 3, cache = true) {
            const config = {}
            // we use force cache so we don't hammer OL servers
            if (cache) {
                config['cache'] = "force-cache"
            }
            const response = await fetch(url, config)
            if (response.status !== 200) {
                if (retries === 0) {
                    throw new Error(`fetch failed with status ${response.status}`)
                }
                return this.fetchWithRetry(url, retries - 1, false)
            }
            return await response.json()
        },
        async getAuthor() {
            this.authorJson = {};
            try {
                this.authorJson = await this.fetchWithRetry(`https://openlibrary.org/authors/${this.authorId}.json`);
            } catch (e) {
                app.status = e.toString();
            }
        },
        async getAuthorWorks(cache = true) {
            this.authorWorksJson = {};
            try {
                this.authorWorksJson = await this.fetchWithRetry(`https://openlibrary.org/authors/${this.authorId}/works.json?limit=1000`, 3, cache);
                app.status = "done";
            } catch (e) {
                app.status = e.toString();
            }
        },
        increaseAuthorId(amount) {
            this.searchUntilSimilarityDirection = amount > 0 ? 'next' : 'previous';
            this.authorId = `OL${this.authorIdNumber + amount}A`;
        },
        setRandomAuthorId() {
            this.searchUntilSimilarityDirection = 'random';
            const highestAuthorId = 9500000; // This is an approximation and should increase over time
            const randomNumber = Math.floor(Math.random() * highestAuthorId) + 1;
            this.authorId = `OL${randomNumber}A`;
        },
        findNextSimilarity() {
            const directions = {
                'next': () => {
                    this.increaseAuthorId(1)
                },
                'previous': () => {
                    this.increaseAuthorId(-1)
                },
                'random': () => {
                    this.setRandomAuthorId()
                }
            }
            if (this.searchUntilSimilarity && this.groupsOfSimilarWorks.length === 0) {
                directions[this.searchUntilSimilarityDirection]();
            }
        },
        updateClipboard(newClip) {
            navigator.clipboard.writeText(newClip).then(() => {
            }, () => {
                /* clipboard write failed */
                app.status = "copy to clipboard failed, please check permissions";
            });
        }
    }
}

const app = Vue.createApp(Counter).mount('#app');
