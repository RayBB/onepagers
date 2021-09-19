const Counter = {
    data() {
        return {
            authorIdTextBox: 'OL6621416A', // this is the value of the box and changes as the box changes
            authorId: 'OL1A', // authorID that is currently being searched/shown. The internal representation after go clicked
            status: '',
            authorWorksJson: {},
            includeSubtitles: true, // should subtitles be included in similarity check
            aggressiveNormalization: true
        }
    },
    mounted() {
        if (localStorage.getItem('includeSubtitles')) {
            this.includeSubtitles = localStorage.getItem('includeSubtitles');
        }
        // Automatically load data if authorId specified in URL
        const queryParams = new URLSearchParams(window.location.search);
        if (queryParams.get("authorId")){
            this.authorId = queryParams.get("authorId");
            this.goBtnClicked();
        }
    },
    watch: {
        includeSubtitles(newStatus) {
            localStorage.setItem('includeSubtitles', newStatus);
        },
        authorId(newValue){
            this.authorIdTextBox = newValue;
            // set URL
            const url = new URL(window.location);
            url.searchParams.set('authorId', newValue);
            window.history.replaceState(null, '', url.toString());
        }
    },
    computed: {
        groupsOfSimilarWorks() {
            const groups = [];
            const similarityThreshold = .9;
            if (!('entries' in this.authorWorksJson)) {
                return []
            }
            // I hate the hack to deep clone
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
            // TODO: this should really just set authorId based on text box
            // the rest should move to authorId watcher
            this.status = `${this.authorId} - searching`;
            this.authorWorksJson = await this.getAuthorWorks(this.authorId);
            this.status = 'done';
        },
        parseKey(s) {
            return s.split("/")[2];
        },
        getWorkIds(works) {
            return works.map(work => this.parseKey(work.key));
        },
        getAuthorWorks(authorId) {
            return fetch(`https://openlibrary.org/authors/${authorId}/works.json?limit=1000`)
                .then(response => response.json())
        },
        increaseAuthorId(amount) {
            this.authorId = `OL${this.authorIdNumber + amount}A`;
            this.goBtnClicked();
        }
    }
}

Vue.createApp(Counter).mount('#app')
