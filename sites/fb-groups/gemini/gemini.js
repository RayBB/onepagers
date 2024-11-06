const { createClient } = require("@supabase/supabase-js");
const {
  GoogleGenerativeAI,
  HarmCategory,
  HarmBlockThreshold,
} = require("@google/generative-ai");

const HOST = "https://XXXXX.supabase.co";

let api_key =
  "KEY HERE";
const supabaseClient = createClient(HOST, api_key);

const API_KEY = "XXXXX";
const MODEL_NAME = "gemini-pro";

const genAI = new GoogleGenerativeAI(API_KEY);
const model = genAI.getGenerativeModel({ model: MODEL_NAME });

function generatePrompt(description) {
  return `This work is very important for my career so lets focus and get it right.
    Your are an assistant that only speaks JSON. Respond in JSON only.

    I need the following JSON filled out about the text:

    {
    "suitable_for_couples": boolean,
    "female_only": boolean,
    "availability_match": boolean,
    "seeking_housing": boolean,
    "about_housing": boolean,
    "reason": {
    ... one for each of the other properties
    }
    }

    Definitions:

    suitable_for_couples: assume true unless it explicitly says no couples allowed or it is only for one person. is true if a couple is allowed.
    female_only: set to true if the listing say only females are eligible to move in.
    availability_match: is the duration at least until the end of April. If lasting beyond april return true. If not specified return true.
    seeking_housing: is this someone who is looking for a place to live?
    about_housing: is this post even about housing at all?
    reason: explain the answers for the above

    Fill out the JSON based on this post:
          ${description}`;
}

async function getGeminiInfo(postDescription) {
  const generationConfig = {
    temperature: 0.9,
    topK: 1,
    topP: 1,
    maxOutputTokens: 2048,
  };

  const safetySettings = [
    {
      category: HarmCategory.HARM_CATEGORY_HARASSMENT,
      threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
    {
      category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
      threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
    {
      category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
      threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
    {
      category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
      threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
  ];

  const parts = [
    {
      text: generatePrompt(postDescription),
    },
  ];

  const result = await model.generateContent({
    contents: [{ role: "user", parts }],
    generationConfig,
    safetySettings,
  });

  const response = result.response;
  let a = response.text();

  function textToJson(text) {
    const temp = text.replaceAll("```", "").replaceAll(/json/gi, "");
    return JSON.parse(temp);
  }

  const responseJson = textToJson(a);
  return responseJson;
}

async function main() {
  const { data: posts, error } = await supabaseClient
    .from("posts")
    .select("*")
    .eq("hide", false)
    .eq("favorite", false)
    .is("gemini_info", null)
    .limit(10)
    .order("date_posted", { ascending: false });
    
    if (posts){
      console.log(`Found ${posts.length} posts to update`);
      posts.forEach(fetchAndUpdatePost);
    }

  async function fetchAndUpdatePost(post) {
    try {
      const response = await getGeminiInfo(post.description);
      post.gemini_info = response;
      const insert_response = await supabaseClient.from("posts").upsert(post);
      console.log("updated post");
    } catch (error) {
      console.log("error", error);
      console.log(post)
    }
  }
}
main();
setInterval(() => main(), 1000 * 20);
