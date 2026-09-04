/*
This is a small tool to help schedule posts in buffer.
We create the posts in a spreadsheet and then paste them in here.
Why not use the buffer bulk scheduler?
Mostly because it doesn't support having links attached but in the text.
Also because we do some custom processing to handle hashtags and links.

*/

// ——————— PROFILE CONFIGURATIONS ———————

let PROFILES = {
  BLUESKY: {
    name: 'Blue Sky',
    id: '67982d52a31978b79c210ae1',
    maxChars: 300,
    canTrimHashtags: true,
    linkInText: false,
  },
  MASTODON: {
    name: 'Mastodon',
    id: '67a5795ecc7f0c250c14d00a',
    maxChars: 500,
    canTrimHashtags: false,
    linkInText: true, // Mastodon requires link in text, not as attachment
  },
  LINKEDIN: {
    name: 'LinkedIn',
    id: '6865a0ebacfb098c69c69dd7',
    maxChars: 3000,
    canTrimHashtags: false,
    linkInText: false,
  },
};

// ——————— LINK METADATA SCRAPING ———————

/**
 * Fetches link metadata from Buffer's scraper API
 * @param {string} url - URL to scrape
 * @returns {Promise<Object>} Metadata object with title, description, images, etc.
 */
async function fetchLinkMetadata(url) {
  // It seems Buffer has a way to block this from working even when run as a fetch in the browser.
  // We'll leave it here but not use it for now.
  const encodedUrl = encodeURIComponent(url);
  const response = await fetch(`https://scraper.buffer.com/?url=${encodedUrl}`, {
    credentials: "omit",
    headers: {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0",
      "Accept": "*/*",
      "Accept-Language": "en-US,en;q=0.5",
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-site",
      "Priority": "u=0"
    },
    referrer: "https://publish.buffer.com/",
    method: "GET",
    mode: "cors"
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch metadata for ${url}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Converts scraped metadata to Buffer's media format
 * @param {string} url - Original URL
 * @param {Object} metadata - Metadata from fetchLinkMetadata
 * @returns {Object} Media object for Buffer API
 */
function buildMediaFromMetadata(url, metadata) {
  // Find the opengraph image (preferred) or first image
  const previewImage = metadata.images?.find(img => img.opengraph)?.url || metadata.images?.[0]?.url;

  return {
    link: metadata.canonicalUrl || url,
    title: metadata.title || "",
    description: metadata.description || "",
    preview: previewImage || "",
    preview_safe: null,
    picture: previewImage || "",
    original_preview: previewImage || "",
  };
}

// ——————— POST GENERATION ———————

/**
 * Generates a post configuration for a specific profile
 * @param {Object} profile - Profile configuration object
 * @param {string} text - Main post text
 * @param {string} link - URL to attach/include
 * @param {string} hashtags - Hashtags to append (space-separated or with spaces)
 * @returns {Promise<Object>} { text, link, media, isValid, error, profile }
 */
async function generatePostForProfile(profile, text, link, hashtags) {
  const result = {
    profile: profile.name,
    profileId: profile.id,
    text: '',
    link: profile.linkInText ? null : link,
    media: null,
    isValid: false,
    error: null,
  };

  // Fetch link metadata if we have a link and it's not embedded in text
  if (link && !profile.linkInText) {
    result.media = { link };
  }

  // Build the full text based on profile requirements
  let fullText = text;
  
  // For Mastodon, include link in text
  if (profile.linkInText && link) {
    fullText = `${text}\n\n${link}`;
  }

  // Try with all hashtags first
  let textWithHashtags = hashtags ? `${fullText}\n\n${hashtags}` : fullText;
  
  if (textWithHashtags.length <= profile.maxChars) {
    result.text = textWithHashtags;
    result.isValid = true;
    return result;
  }

  // If over limit and can trim hashtags, try trimming them one by one
  if (profile.canTrimHashtags && hashtags) {
    // Split hashtags into array (handles both space-separated and newline-separated)
    const hashtagArray = hashtags.trim().split(/\s+/).filter(tag => tag.startsWith('#'));
    
    // Try removing hashtags one by one from the end
    for (let i = hashtagArray.length - 1; i >= 0; i--) {
      const remainingHashtags = hashtagArray.slice(0, i).join(' ');
      const testText = remainingHashtags 
        ? `${fullText}\n\n${remainingHashtags}`
        : fullText;
      
      if (testText.length <= profile.maxChars) {
        result.text = testText;
        result.isValid = true;
        const trimmedCount = hashtagArray.length - i;
        result.warning = `Trimmed ${trimmedCount} hashtag${trimmedCount > 1 ? 's' : ''} to fit ${profile.name} character limit (kept ${i} of ${hashtagArray.length})`;
        return result;
      }
    }
    
    // Even without hashtags, still too long
    if (fullText.length > profile.maxChars) {
      result.error = `Post exceeds ${profile.name} character limit even without hashtags (${fullText.length}/${profile.maxChars} chars)`;
      return result;
    }
    
    // This shouldn't happen, but just in case
    result.text = fullText;
    result.isValid = true;
    result.warning = `All hashtags trimmed to fit ${profile.name} character limit`;
    return result;
  }

  // Can't trim hashtags for this profile - return error
  result.error = `Post exceeds ${profile.name} character limit (${textWithHashtags.length}/${profile.maxChars} chars)`;
  if (!profile.canTrimHashtags && hashtags) {
    result.error += `. ${profile.name} does not support hashtag trimming.`;
  }
  
  return result;
}

/**
 * Schedules posts to all three platforms (Blue Sky, Mastodon, LinkedIn)
 * Only posts if ALL three platforms can be successfully configured
 * @param {string} text - Main post text
 * @param {string} link - URL to attach/include
 * @param {string} hashtags - Hashtags to append
 * @returns {Promise} Result of posting or error details
 */
async function schedulePosts(text, link, hashtags) {
  // Generate configs for all three profiles (now async)
  const configs = await Promise.all([
    generatePostForProfile(PROFILES.BLUESKY, text, link, hashtags),
    generatePostForProfile(PROFILES.MASTODON, text, link, hashtags),
    generatePostForProfile(PROFILES.LINKEDIN, text, link, hashtags),
  ]);

  // Check if all configs are valid
  const invalidConfigs = configs.filter(c => !c.isValid);
  
  if (invalidConfigs.length > 0) {
    const errors = invalidConfigs.map(c => `${c.profile}: ${c.error}`).join('\n');
    throw new Error(`Cannot schedule posts. The following platforms failed validation:\n${errors}`);
  }

  // Log any warnings
  const warnings = configs.filter(c => c.warning);
  if (warnings.length > 0) {
    console.warn('Warnings:');
    warnings.forEach(c => console.warn(`- ${c.profile}: ${c.warning}`));
  }

  // All valid - prepare for Buffer API
  console.log('All platforms validated successfully. Scheduling posts...');
  
  // Post to each platform with its specific configuration
  const results = await Promise.all(
    configs.map(config => 
      postToBuffer({
        text: config.text,
        profile_ids: [config.profileId],
        media: config.media, // Use media from config (includes scraped metadata)
      })
    )
  );

  return {
    success: true,
    configs: configs.map(c => ({
      profile: c.profile,
      textLength: c.text.length,
      warning: c.warning,
      hasMedia: !!c.media,
    })),
    results,
  };
}

/**
 * Schedules multiple posts from a TSV string
 * @param {string} tsvString - TSV data with columns: text, url, hashtags
 * @returns {Promise} Results for all posts with success/failure details
 */
async function schedulePostsFromTSV(tsvString) {
  // Parse TSV into rows
  const lines = tsvString.trim().split('\n');
  
  if (lines.length === 0) {
    throw new Error('TSV string is empty');
  }

  // Check if first line is a header (contains "text", "url", or "hashtags")
  const firstLine = lines[0].toLowerCase();
  const hasHeader = firstLine.includes('text') || firstLine.includes('url') || firstLine.includes('hashtag');
  const dataLines = hasHeader ? lines.slice(1) : lines;

  if (dataLines.length === 0) {
    throw new Error('No data rows found in TSV');
  }

  console.log(`Processing ${dataLines.length} post(s) from TSV...`);

  // Process each row
  const results = [];
  
  for (let i = 0; i < dataLines.length; i++) {
    const line = dataLines[i].trim();
    if (!line) continue; // Skip empty lines

    const rowNumber = hasHeader ? i + 2 : i + 1; // For error reporting
    const columns = line.split('\t');

    if (columns.length < 2) {
      results.push({
        row: rowNumber,
        success: false,
        error: `Invalid TSV format: expected at least 2 columns (text, url), got ${columns.length}`,
      });
      continue;
    }

    const [text, url, hashtags = ''] = columns;

    try {
      const result = await schedulePosts(text.trim(), url.trim(), hashtags.trim());
      results.push({
        row: rowNumber,
        success: true,
        text: text.trim(),
        url: url.trim(),
        ...result,
      });
      console.log(`✅ Row ${rowNumber}: Successfully scheduled`);
    } catch (error) {
      results.push({
        row: rowNumber,
        success: false,
        text: text.trim(),
        url: url.trim(),
        error: error.message,
      });
      console.error(`❌ Row ${rowNumber}: ${error.message}`);
    }
  }

  // Summary
  const successCount = results.filter(r => r.success).length;
  const failureCount = results.filter(r => !r.success).length;

  console.log(`\n📊 Summary: ${successCount} succeeded, ${failureCount} failed out of ${results.length} total`);

  return {
    total: results.length,
    succeeded: successCount,
    failed: failureCount,
    results,
  };
}

// ——————— BUFFER API ———————

/**
 * Posts to Buffer with optional media metadata
 * @param {Object} params - Post parameters
 * @param {string} params.text - Post text content
 * @param {string[]} params.profile_ids - Array of Buffer profile IDs
 * @param {Object} [params.media] - Optional media object with link, title, description, preview, etc.
 * @returns {Promise} Fetch response from Buffer API
 */
async function postToBuffer({ text, profile_ids, media }) {
  if (!text || !profile_ids?.length) {
    throw new Error("text and profile_ids are required");
  }

  const body = JSON.stringify({
    args: JSON.stringify({
      url: "/1/updates/create.json",
      HTTPMethod: "POST",
      args: {
        text,
        profile_ids,
        media,
        attachment: true,
        shorten: true,
        share_mode: "addToQueue",
        now: false,
        top: false,
        is_draft: false,
        scheduling_type: "direct",
        fb_text: "",
        entities: null,
        annotations: [],
        via: null,
        duplicated_from: null,
        created_source: "channel",
        channel_data: null,
        tags: [],
        ai_assisted: false,
        channelGroupIds: [],
      }
    })
  });

  return fetch("https://publish.buffer.com/rpc/composerApiProxy", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0",
      "Accept": "application/json",
    },
    referrer: "https://publish.buffer.com/all-channels",
    body,
  });
}

// ——————— EXAMPLE USAGE ———————

// Example 1: Normal case - should work for all platforms
// schedulePosts(
//   "Urbanism Now Issue 45 is out now! Check out our latest insights on 15-minute cities and open data.",
//   "https://urbanismnow.substack.com/p/45-x-minute-cities-and-open-data",
//   "#urbanism #cities #planning #opendata"
// )
//   .then(result => {
//     console.log('✅ Success!', result);
//   })
//   .catch(error => {
//     console.error('❌ Error:', error.message);
//   });

// Example 2: Schedule multiple posts from TSV
const tsvData = `

A beautiful visualization and analysis of the 2023 Türkiye-Syria earthquake response shows how thousands of OpenStreetMap volunteers traced more than 2 million buildings and 72,000 kilometers of roads to support rescue and aid logistics. This is now underway for Venezuela and anyone can volunteer.	https://sheets.works/data-viz/strangers-draw-maps	#urbanism #urbanplanning #OpenStreetMap #HumanitarianAid #DisasterResponse
Tokyo’s reliance on “mamachari” bikes, primarily used by women for caregiving, is threatened by new traffic penalties that penalize sidewalk riding without offering protected bike infrastructure. Grassroots initiatives advocating for safer streets and inclusive urban planning.	https://thecityfix.com/blog/protecting-tokyos-cyclists-is-a-gender-equity-issue/	#urbanism #urbanplanning #Mamachari #CyclingSafety #GenderInclusiveCity
Urbanist Jeffery Tompkins argues that front porches are vital social infrastructure that fosters community and counters modern housing designs that inhibit neighborly interaction. He advocates to reintroduce usable porches to combat social isolation.	https://www.thinkingbigbythinkingsmall.com/p/porches-as-social-infrastructure	#urbanism #urbanplanning #FrontPorches #SocialInfrastructure #CommunityBuilding
Cyclearchive.com offers a free, browsable online library of vintage cycling magazines and books from the 1860s-1940s, featuring deep-linked articles and a full-text search function to explore cycling history and early innovations.	https://cyclearchive.com/	#urbanism #urbanplanning #cyclinghistory #vintagecycling #bikelife
Morning Brew’s latest video is about how modular construction offers a pathway to build housing faster and more sustainably, yet the industry struggles to scale in the U.S. due to fragmented zoning, risk-averse financing, and a lack of standardized building codes. 	https://www.youtube.com/watch?v=2pbYafEcsbk	#urbanism #urbanplanning #ModularConstruction #AffordableHousing #SustainableBuilding
Global Cycling Network is back with Why Aren’t Dangerous Drivers Punished? It advocated for an ‘aviation-style’ approach that prioritizes learning from incidents to prevent future harm.	https://www.youtube.com/watch?v=dHRfClVJg70	#urbanism #urbanplanning #RoadSafety #CyclingSafety #VisionZero
See all our new jobs at https://urbanismnow.com/jobs below are a select few.	https://urbanismnow.com/jobs	#urbanism #urbanplanning #CityPlanning #UrbanDesign #JobSearch
EIT Urban Mobility is hiring a regional innovation scheme assistant to support the coordination of the EIT Community Officer Network across 29 countries. €18k - €22k salary. Apply by July 8.	https://eiturbanmobility.bamboohr.com/careers/135	#urbanism #urbanplanning #Innovation #Mobility #EIT
Cascadia Partners is hiring a senior associate, urban data & policy analysis to lead data-driven spatial planning projects, managing budgets and technical production for initiatives like housing policy and comprehensive plans. $85k - $100k salary. Apply by July 26.	https://www.cascadia-partners.com/senior-associate	#urbanism #urbanplanning #UrbanData #HousingPolicy #SpatialPlanning
The Brussels Centre for Urban Studies is hiring a four-year postdoc researcher on polluter and wealth elites to lead collaborative research and co-supervise PhD students within the Chair in Decarbonisation and Justice.	https://urbanstudies.brussels/news-events/vacancy-postdoc-researcher-polluter-and-wealth-elites	#urbanism #urbanplanning #Decarbonisation #Sustainability #UrbanStudies

`;

schedulePostsFromTSV(tsvData)
  .then(result => {
    console.log('📊 Batch Results:', result);
    console.log(`Success: ${result.succeeded}/${result.total}`);
  })
  .catch(error => console.error('❌ Error:', error.message));

