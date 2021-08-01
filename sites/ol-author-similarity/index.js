function getAuthorWorks(authorId) {
    return fetch(`https://openlibrary.org/authors/${authorId}/works.json?limit=1000`)
      .then(response => response.json())
  }

function getSimilarWorksByTitle(mainWork, allWorks, similarityThreshold = .9){
    // main work is the one we want to find similar works to
    const worksExcludingMainWork = allWorks.filter(work => work !== mainWork);
    const titles = worksExcludingMainWork.map(work => work.title);

    const similarities = stringSimilarity.findBestMatch(mainWork.title, titles);
    const similarWorks = similarities.ratings
    .map((result, index)=>{
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
}
  

function findGroupsOfSimilar(authorWorks, similarityThreshold = .9){
    const groups = [];
    let entries = authorWorks.entries;
    console.log("Entry count:", entries.length);
    while (entries.length > 1) {
        const mainWork = entries.shift();
        const similarWorks = getSimilarWorksByTitle(mainWork, entries, similarityThreshold);
        if (similarWorks.maxSimilarity > similarityThreshold) {
            console.log(similarWorks,
                similarWorks.works.map(work => work.title),
                similarWorks.works.map(work => work.key.replace("/works/","")).join(',')
                );
            groups.push(similarWorks);
            entries = entries.filter(entry => !similarWorks.works.includes(entry));
        }
    }
    return groups;
}

function buttonClicked(){
    const authorId = document.getElementById("authorId").value.match(/OL\d+A/gi)[0];
    console.log("searching for works by", authorId);

    getAuthorWorks(authorId)
    .then(authorWorks => {
        const groups = findGroupsOfSimilar(authorWorks);
        document.getElementById("results").innerHTML = generateResultsHTML(groups, authorId)
    })
}
function generateResultsHTML(groups, authorId){
    let html = "";
    groups.forEach(group => {
        html += "<ul>"
        group.works.forEach(work => {
            const workId = work.key.replace("/works/","");
            html += `<li>${work.title} (<a href="https://openlibrary.org/works/${workId}/">${workId}</a>)</li>`
        })
        html += "</ul>"
        const workIds = group.works.map(work => work.key.replace("/works/",""))
        html += `<a href="https://openlibrary.org/authors/${authorId}/?q=${workIds.join('+OR+')}">Search for these works</a> | `
        html += `<span>${workIds.join(',')}</span>`
        html += "<hr>"
    })
    return html
}
const searchButton = document.getElementById("searchBtn");
console.log(searchButton)
searchButton.addEventListener("click", e=>buttonClicked(e));