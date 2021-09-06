function getAuthorWorks(authorId) {
    return fetch(`https://openlibrary.org/authors/${authorId}/works.json?limit=1000`)
      .then(response => response.json())
  }

function getSimilarWorksByTitle(mainWork, allWorks, similarityThreshold = .9){
    // main work is the one we want to find similar works to
    const worksExcludingMainWork = allWorks.filter(work => work !== mainWork);
    const titles = worksExcludingMainWork.map(work => work.title.toLowerCase());

    const similarities = stringSimilarity.findBestMatch(mainWork.title.toLowerCase(), titles);
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

function getAuthorId(){
    return document.getElementById("authorId").value.match(/OL\d+A/gi)[0].toUpperCase();
}

function goBtnClicked(){
    authorId = getAuthorId()
    console.log("searching for works by", authorId);
    document.getElementById("results").innerHTML = `<p>${authorId} - searching</p>`;
    getAuthorWorks(authorId)
    .then(authorWorks => {
        const groups = findGroupsOfSimilar(authorWorks);
        document.getElementById("results").innerHTML = generateResultsHTML(groups, authorId);
        document.getElementById("author-link").innerHTML = generateShowAuthorHTML(authorId);
    })
}

function generateShowAuthorHTML(authorId) {
  let html = "<a href="https://openlibrary.org/authors/${authorId}">${authorId}</a>"
  return html
}

function generateResultsHTML(groups, authorId){
    let html = "";
    if (groups.length == 0){
        html = `<p>${authorId} - no similar works found</p>`;
    }
    groups.forEach(group => {
        html += "<ul>"
        group.works.forEach(work => {
            const workId = work.key.replace("/works/","");
            html += `<li>${work.title} (<a target="_blank" href="https://openlibrary.org/works/${workId}/">${workId}</a>)</li>`
        })
        html += "</ul>"
        const workIds = group.works.map(work => work.key.replace("/works/",""))
        html += `<a target="_blank" href="https://openlibrary.org/authors/${authorId}/?q=${workIds.join('+OR+')}">Search</a> | `
        html += `<a target="_blank" href="https://testing.openlibrary.org/works/merge?records=${workIds.join(',')}">Merge</a> | `
        html += `<span>${workIds.join(',')}</span>`
        html += "<hr>"
    })
    return html
}

function goToPrev(){
    document.getElementById("authorId").value = "OL" + (parseInt(getAuthorId().match(/\d+/)[0])-1) + "A";
    goBtnClicked();
}

function goToNext(){
    document.getElementById("authorId").value = "OL" + (parseInt(getAuthorId().match(/\d+/)[0])+1) + "A";
    goBtnClicked();
}

document.getElementById("prevBtn").addEventListener("click", goToPrev);
document.getElementById("nextBtn").addEventListener("click", goToNext);
document.getElementById("searchBtn").addEventListener("click", goBtnClicked);