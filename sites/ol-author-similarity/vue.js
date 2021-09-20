const Counter = {
    data() {
        return {
            authorIdTextBox: 'OL6621416A', // this is the value of the box and changes as the box changes
            authorId: 'OL6621416A', // authorID that is currently being searched/shown. The internal representation after go clicked
            status: '',
            authorWorksJson: {},
            includeSubtitles: true, // should subtitles be included in similarity check
            aggressiveNormalization: true,
            settingsVisible: true,
            coversVisible: true,
            dataToRemember: ['includeSubtitles', 'aggressiveNormalization', 'settingsVisible', 'coversVisible'],
        }
    },
    mounted() {
        // Automatically load data if authorId specified in URL
        const queryParams = new URLSearchParams(window.location.search);
        if (queryParams.get("authorId")) {
            this.authorId = queryParams.get("authorId");
        }
    },
    created(){
        for (const dataName of this.dataToRemember){
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
            this.authorWorksJson = await this.getAuthorWorks(this.authorId);
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
            this.authorId = this.authorIdTextBox;
        },
        parseKey(s) {
            return s.split("/")[2];
        },
        getWorkIds(works) {
            return works.map(work => this.parseKey(work.key));
        },
        getAuthorWorks(authorId) {
            return fetch(`https://openlibrary.org/authors/${authorId}/works.json?limit=1000`)
                .then(response => {
                    if (!response.ok) {
                        // using app here since "this" in a call back doesn't refer to the vue instance
                        app.status = "Error requesting works"
                        return {}
                    }
                    app.status = "done"
                    return response.json()
                })
        },
        increaseAuthorId(amount) {
            this.authorId = `OL${this.authorIdNumber + amount}A`;
        },
        setRandomAuthorId() {
            const highestAuthorId = 9500000; // This is an approximation and should increase over time
            const randomNumber = Math.floor(Math.random() * highestAuthorId) + 1;
            this.authorId = `OL${randomNumber}A`;
        },
        updateClipboard(newClip) {
            navigator.clipboard.writeText(newClip).then(() => {
            }, () => {
                /* clipboard write failed */
                app.status = "copy to clipboard failed, please check permissions"
            });
        }
    }
}

const app = Vue.createApp(Counter).mount('#app')
