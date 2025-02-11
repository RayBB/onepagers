# Open Library Wikidata Matcher

This is kind of like Wikimedia's [mix-n-match](https://meta.wikimedia.org/wiki/Mix%27n%27match) tool.
But we're pulling authors from Wikidata to connect with OL instead of the other way around.
Why? Mostly because there can be many duplicate authors in OL so I think wikidata is more reliable now.

Required Features
- [] Query Wikidata for authors that have a Librivox ID but not an Open Library ID
- [] Show the list of authors that need to be matched on the page
   - [] Link to Wikidata, Wikidata Resonator, Librivox, and Open Library Search
- [] Show how many OL search results for each author
   - URL for queries: https://openlibrary.org/search/authors.json?q=Cory Doctorow

Here's our query:
```
SELECT ?human ?humanLabel ?libriVoxAuthorId WHERE {
  ?human wdt:P31 wd:Q5.  # filter for humans (P31 is "instance of")
  ?human wdt:P1899 ?libriVoxAuthorId.  # filter for humans with a Librivox author ID
  MINUS {  # exclude humans with an Open Library ID
    ?human wdt:P648 ?openLibraryId.  # filter for humans with an Open Library ID (P648 is "Open Library ID")
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
```
