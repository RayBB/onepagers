const Counter = {
    data() {
        return {
            min: 11,
            max: 99,
            first: 0,
            second: 11,
            showAnswer: false,
        }
    },
    computed: {
        solution() {
            return this.first * this.second;
        }
    },
    created() {
        this.generateNewRandoms()
    },
    mounted() {
        let self = this;
        window.addEventListener('keyup', function (event) {
            if (event.code === 'Space') {
                self.nextButton();
            }
        });
    },
    methods: {
        getRandomInt(min, max) {
            min = Math.ceil(min);
            max = Math.floor(max);
            return Math.floor(Math.random() * (max - min) + min); //The maximum is exclusive and the minimum is inclusive
        },
        generateNewRandoms() {
            this.first = this.getRandomInt(this.min, this.max);
            //this.second = this.getRandomInt(this.min, this.max);
        },
        nextButton() {
            if (this.showAnswer == true) {
                this.generateNewRandoms();
                this.speak(this.first)
            } else {
                this.speak(this.solution)
            }
            this.showAnswer = !this.showAnswer;
        },
        speak(words) {
            let synth = window.speechSynthesis;
            if (synth.speaking) {
                console.error('speechSynthesis.speaking');
                return;
            }
            var utterThis = new SpeechSynthesisUtterance(words);
            utterThis.onend = function (event) {
                console.log('SpeechSynthesisUtterance.onend');
            }
            utterThis.onerror = function (event) {
                console.error('SpeechSynthesisUtterance.onerror');
            }
            utterThis.voice = synth.getVoices().filter(v => v.lang == "en-US")[0];
            utterThis.pitch = 1 //pitch.value;
            utterThis.rate = 1 //rate.value;
            synth.speak(utterThis);
        }
    }
}

Vue.createApp(Counter).mount('#app')
