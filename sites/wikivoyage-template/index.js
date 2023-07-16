const App = {
  data() {
    return { input: "" };
  },
  computed: {
    solution() {
      return this.input.split("\n").map(createGoTemplate).join("\n");
    },
  },
};

function createGoTemplate(line) {
  return `*{{listing | type=go | name=${line}}}`;
}

Vue.createApp(App).mount("#app");
