export type Lang = "en" | "hi";

const STRINGS = {
  hello: { en: "Hi! I'm Fixy", hi: "नमस्ते! मैं फ़िक्सी हूँ" },
  whatNeedsFixing: { en: "What needs fixing?", hi: "क्या ठीक करना है?" },
  talk: { en: "Talk", hi: "बोलें" },
  scan: { en: "Scan", hi: "स्कैन" },
  type: { en: "Type", hi: "लिखें" },
  cameraSoon: { en: "Camera is coming soon. Type for now!", hi: "कैमरा जल्द आ रहा है। अभी लिखकर बताएं!" },
  voiceSoon: { en: "Voice is coming soon. Type for now!", hi: "आवाज़ जल्द आ रही है। अभी लिखकर बताएं!" },
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
  language: { en: "Switch to Hindi", hi: "Switch to English" },
} as const;

export type StringKey = keyof typeof STRINGS;

export function t(key: StringKey, lang: Lang): string {
  return STRINGS[key][lang];
}
