export type Lang = "en" | "hi";

const STRINGS = {
  hello: { en: "Hi! I'm Fixy", hi: "नमस्ते! मैं फ़िक्सी हूँ" },
  whatNeedsFixing: { en: "What needs fixing?", hi: "क्या ठीक करना है?" },
  talk: { en: "Talk", hi: "बोलें" },
  scan: { en: "Scan", hi: "स्कैन" },
  type: { en: "Type", hi: "लिखें" },
  voiceUnsupported: {
    en: "Voice isn't supported in this browser. Type instead!",
    hi: "इस ब्राउज़र में आवाज़ नहीं चलती। लिखकर बताएं!",
  },
  listening: { en: "Listening…", hi: "सुन रहा हूँ…" },
  speak: { en: "Speak", hi: "बोलें" },
  looking: { en: "Looking at your photo…", hi: "आपकी फ़ोटो देख रहा हूँ…" },
  photo: { en: "📷 Photo", hi: "📷 फ़ोटो" },
  photoFailed: {
    en: "I couldn't read that photo. Tell me what's wrong instead?",
    hi: "फ़ोटो समझ नहीं पाया। लिखकर बताएं क्या खराबी है?",
  },
  photoNote: {
    en: "The photo goes to Google Gemini and isn't stored. Keep people out of the frame.",
    hi: "फ़ोटो Google Gemini को जाती है और सेव नहीं होती। फ़्रेम में लोग न हों।",
  },
  whatsWrong: { en: "What's wrong with it?", hi: "इसमें क्या खराबी है?" },
  placeholder: { en: "e.g. my fan hums but won't spin", hi: "जैसे: पंखा आवाज़ करता है पर घूमता नहीं" },
  message: { en: "Message", hi: "संदेश" },
  send: { en: "Send", hi: "भेजें" },
  back: { en: "Back", hi: "वापस" },
  yes: { en: "Yes", hi: "हाँ" },
  no: { en: "No", hi: "नहीं" },
  notSure: { en: "Not sure", hi: "पता नहीं" },
  thinking: { en: "Fixy is thinking", hi: "फ़िक्सी सोच रहा है" },
  wakingUp: { en: "Waking up… this can take a minute.", hi: "जाग रहा हूँ… एक मिनट लग सकता है।" },
  offline: { en: "I couldn't connect. Try again?", hi: "कनेक्ट नहीं हो पाया। फिर कोशिश करें?" },
  retry: { en: "Try again", hi: "फिर कोशिश करें" },
  startOver: { en: "Start over", hi: "फिर से शुरू करें" },
  likely: { en: "Likely", hi: "संभावना" },
  showMeHow: { en: "Show me how", hi: "कैसे करें, दिखाओ" },
  whoToCall: { en: "Who to call", hi: "किसे बुलाएं" },
  curated: { en: "Curated", hi: "जांचा-परखा" },
  curatedHint: {
    en: "From cited sources. Expert review pending.",
    hi: "स्रोतों से लिया गया। विशेषज्ञ की जांच बाकी है।",
  },
  start: { en: "Start", hi: "शुरू करें" },
  next: { en: "Next", hi: "आगे" },
  min: { en: "min", hi: "मिनट" },
  estimate: { en: "estimate", hi: "अनुमान" },
  free: { en: "Free", hi: "मुफ़्त" },
  youNeed: { en: "You need", hi: "आपको चाहिए" },
  powerOffFirst: { en: "Power off at the MCB first", hi: "पहले MCB से बिजली बंद करें" },
  sources: { en: "Sources", hi: "स्रोत" },
  didItWork: { en: "Did it work?", hi: "क्या ठीक हो गया?" },
  yay: { en: "Yay, it works!", hi: "वाह, ठीक हो गया!" },
  sorry: { en: "Sorry it didn't work.", hi: "माफ़ कीजिए, ठीक नहीं हुआ।" },
  tryNext: { en: "It could also be the", hi: "यह भी हो सकता है:" },
  askPro: { en: "An electrician can check it safely.", hi: "इलेक्ट्रीशियन इसे सुरक्षित रूप से जांच सकता है।" },
  fixAnother: { en: "Fix something else", hi: "कुछ और ठीक करें" },
  call112: { en: "Call 112", hi: "112 पर कॉल करें" },
  goBack: { en: "Go back", hi: "वापस जाएं" },
  tip: { en: "Tip", hi: "सुझाव" },
  onlyFans: {
    en: "For now I can help with ceiling fans, extension boards, earphones, and toys or remotes. More soon!",
    hi: "अभी मैं छत के पंखे, एक्सटेंशन बोर्ड, ईयरफ़ोन, और खिलौने या रिमोट में मदद कर सकता हूँ। जल्द और भी!",
  },
  noneOfThese: { en: "None of these", hi: "इनमें से कोई नहीं" },
  askAnyway: { en: "Ask anyway", hi: "फिर भी पूछें" },
  askFollowUp: { en: "Ask a follow-up question", hi: "कोई और सवाल पूछें" },
  fromSources: { en: "From sources", hi: "स्रोतों से" },
  checked: { en: "Checked", hi: "जांचा गया" },
  checkedHint: {
    en: "A second AI model checked each point against its source.",
    hi: "दूसरे AI मॉडल ने हर बात को उसके स्रोत से मिलाकर जांचा।",
  },
  notChecked: { en: "Not checked", hi: "जांचा नहीं गया" },
  notCheckedHint: {
    en: "Based on the sources below, but the second check didn't run. Use with care.",
    hi: "नीचे दिए स्रोतों पर आधारित, पर दूसरी जांच नहीं हुई। सावधानी से इस्तेमाल करें।",
  },
  aiSuggestion: { en: "AI suggestion", hi: "AI सुझाव" },
  unverified: { en: "Unverified", hi: "जांचा नहीं गया" },
  searchingWeb: { en: "Searching the web…", hi: "वेब पर खोज रहा हूँ…" },
  openGuide: { en: "Open the full guide", hi: "पूरी गाइड खोलें" },
  buyPart: { en: "Buy the part", hi: "पार्ट खरीदें" },
  buyNote: {
    en: "Search results open on the store. Check the spec matches before you buy.",
    hi: "दुकान पर खोज के नतीजे खुलेंगे। खरीदने से पहले स्पेसिफ़िकेशन मिलाएं।",
  },
  findShop: { en: "Find a repair shop", hi: "रिपेयर की दुकान खोजें" },
  shopQuery: { en: "repair shop near me", hi: "repair shop near me" },
  findElectrician: { en: "Find an electrician nearby", hi: "पास में इलेक्ट्रीशियन खोजें" },
  tooMany: {
    en: "Lots of questions right now! Please try again in a minute.",
    hi: "अभी बहुत सवाल आ रहे हैं! एक मिनट बाद फिर कोशिश करें।",
  },
  privacy: { en: "Privacy & terms", hi: "गोपनीयता और शर्तें" },
  stuck: { en: "I'm stuck", hi: "समझ नहीं आया" },
  askStep: { en: "Ask about this step", hi: "इस स्टेप के बारे में पूछें" },
  stuckHint: {
    en: "Type, talk, or send a photo of what you see.",
    hi: "लिखें, बोलें, या जो दिख रहा है उसकी फ़ोटो भेजें।",
  },
  readAloud: { en: "Read aloud", hi: "पढ़कर सुनाएं" },
  voiceOn: { en: "Voice on", hi: "आवाज़ चालू" },
  voiceOff: { en: "Voice off", hi: "आवाज़ बंद" },
  sendPhoto: { en: "Send a photo", hi: "फ़ोटो भेजें" },
  sayNext: {
    en: "Say \"next\", \"repeat\", or ask a question.",
    hi: "\"आगे\", \"दोबारा\" बोलें, या सवाल पूछें।",
  },
  tryThese: { en: "Try these steps", hi: "ये स्टेप आज़माएं" },
  fixedIt: { en: "Fixed it!", hi: "ठीक हो गया!" },
  stillBroken: { en: "Still not working", hi: "अभी भी खराब है" },
  greatJob: { en: "Great job! Glad it's working again.", hi: "शाबाश! अच्छा हुआ कि फिर से चल रहा है।" },
  nextOptions: {
    en: "Sorry! Send me a photo or tell me more, and I'll look again. Or get a repair shop to check it.",
    hi: "माफ़ कीजिए! फ़ोटो भेजें या और बताएं, मैं फिर देखूंगी। या किसी रिपेयर दुकान से जांच करवाएं।",
  },
  generalTips: { en: "General tips", hi: "सामान्य सुझाव" },
  language: { en: "Switch to Hindi", hi: "Switch to English" },
} as const;

export type StringKey = keyof typeof STRINGS;

// Common Hindi words typed in Latin letters (Hinglish). Ambiguous English words like "me" and
// "to" are left out.
const HINGLISH =
  /\b(hai|hain|nahi|nahin|nhi|nai|kya|kaise|kyu|kyon|kyun|mera|meri|mere|hamara|kar|kr|karu|karun|karna|raha|rha|rahi|rhi|rahe|gaya|gya|gayi|gyi|ka|ki|ke|ko|se|mein|aur|bhi|chal|chalta|chalti|kaam|kam|batao|bata|thik|theek|abhi|pankha|bijli|toh|jal|band|wala|wali|ab|jaldi|accha|acha|haan)\b/gi;
const ENGLISH =
  /\b(the|is|it|my|not|does|doesn't|won't|isn't|what|how|why|and|with|when|working|can|i|stopped|broken|this)\b/gi;

/** The language a message is written in: Hindi script or Hinglish → "hi", clear English → "en",
 * too short or mixed to tell → null (keep the current language). */
export function detectLang(text: string): Lang | null {
  if (/[\u0900-\u097F]/.test(text)) return "hi";
  const hi = text.match(HINGLISH)?.length ?? 0;
  const en = text.match(ENGLISH)?.length ?? 0;
  if (hi >= 2 && hi > en) return "hi";
  if (en >= 2 && hi === 0) return "en";
  return null;
}

export function t(key: StringKey, lang: Lang): string {
  return STRINGS[key][lang];
}
