// Citizen-facing strings. Keep these free of technical terms (model, engine or library
// names, "RAG", "LLM", "ASR", latency, confidence scores): operator strings live in
// adminTranslations.ts, which only the lazily loaded admin screens import.

export interface HowItWorksStep {
  title: string;
  desc: string;
}

export interface SampleQuery {
  tag: string;
  query: string;
  meaning: string;
}

export interface TranslationDictionary {
  nav: {
    home: string;
    voice: string;
    chat: string;
    docs: string;
    manageDocs: string;
    qualityChecks: string;
    dialectBadge: string;
    tagline: string;
  };
  status: {
    checking: string;
    available: string;
    unavailable: string;
    unavailableHint: string;
  };
  home: {
    badge: string;
    title: string;
    subtitle: string;
    description: string;
    btnVoice: string;
    btnChat: string;
    btnDocs: string;
    howTitle: string;
    steps: HowItWorksStep[];
    demoTitle: string;
    demoSubtitle: string;
    askButton: string;
    sampleQueries: SampleQuery[];
  };
  voice: {
    title: string;
    subtitle: string;
    recordStart: string;
    recordStop: string;
    recordingTime: string;
    recordingLength: string;
    uploadAudio: string;
    processing: string;
    previewTitle: string;
    yourRecording: string;
    editTranscript: string;
    understoodAs: string;
    saveEdit: string;
    submitToChat: string;
    uncertainNotice: string;
    noAudioRecorded: string;
    requestFailed: string;
    micPermissionError: string;
  };
  chat: {
    title: string;
    subtitle: string;
    inputPlaceholder: string;
    sendButton: string;
    thinking: string;
    sourcesTitle: string;
    page: string;
    viewEnglish: string;
    translating: string;
    englishLabel: string;
    audioListen: string;
    dialectBadge: string;
    ratePrompt: string;
    rateCorrectionPlaceholder: string;
    submitFeedback: string;
    feedbackThanks: string;
    emptyChatPrompt: string;
    errorAnswer: string;
    actionFailed: string;
    checkSource: string;
  };
  docs: {
    title: string;
    subtitle: string;
    countLabel: string;
    grNumber: string;
    issued: string;
    openOfficial: string;
    superseded: string;
    emptyList: string;
    loadError: string;
  };
  dialects: {
    standard: string;
    varhadi: string;
  };
  footer: {
    text: string;
  };
}

// The sample questions are asked in Marathi or Varhadi in every UI language.
const VARHADI_LOAN_QUERY = 'मले शेतीसाठी कर्जमाफी आणि शासकीय अनुदान कसं भेटन ते सांगा.';
const NAMO_QUERY = 'नमो शेतकरी महासन्मान निधी योजनेसाठी पात्रता निकष आणि आवश्यक कागदपत्रे कोणती आहेत?';
const CROP_QUERY = 'अतिवृष्टीमुळे कापूस आणि सोयाबीन पिकाचे नुकसान झाल्यास नुकसान भरपाई कशी मागता येईल?';

export const translations: Record<string, TranslationDictionary> = {
  // 1. Marathi (प्रमाण मराठी)
  mr: {
    nav: {
      home: 'मुख्य पान',
      voice: 'आवाज सहाय्यक',
      chat: 'संभाषण',
      docs: 'शासकीय कागदपत्रे',
      manageDocs: 'कागदपत्र व्यवस्थापन',
      qualityChecks: 'गुणवत्ता तपासणी',
      dialectBadge: 'बोलीभाषा जाणकार',
      tagline: 'स्थानिक भाषा व बोलीभाषा बहुभाषिक सहाय्यक'
    },
    status: {
      checking: 'सेवा तपासत आहे…',
      available: 'सेवा उपलब्ध',
      unavailable: 'सेवा तात्पुरती अनुपलब्ध',
      unavailableHint: 'सध्या उत्तरे देण्यात अडचण येत आहे, त्यामुळे उत्तरे अपूर्ण असू शकतात. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा.'
    },
    home: {
      badge: 'अधिकृत शासकीय कागदपत्रांतून, पान क्रमांकासह उत्तरे',
      title: 'BharatLangTech AI',
      subtitle: 'स्थानिक भाषा आणि बोलीभाषा जाणणारा बहुभाषिक कृषी व शासकीय योजना सहाय्यक',
      description: 'विदर्भातील वऱ्हाडी आणि प्रमाण मराठी बोलणाऱ्या शेतकऱ्यांसाठी. नमो शेतकरी, पीएम-किसान, पीक विमा व कर्जमुक्ती योजनांबद्दल प्रश्न विचारा; उत्तरे महाराष्ट्र शासनाच्या अधिकृत निर्णयांवर आधारित असतात.',
      btnVoice: 'बोलून प्रश्न विचारा',
      btnChat: 'टाइप करून विचारा',
      btnDocs: 'शासकीय कागदपत्रे पहा',
      howTitle: 'हे कसे काम करते',
      steps: [
        {
          title: 'बोलून किंवा टाइप करून विचारा',
          desc: 'मराठी, वऱ्हाडी, हिंदी किंवा इंग्रजीत विचारा. बोललेला प्रश्न आधी मजकुरात दिसतो; तो तपासून हवे तर दुरुस्त करा.'
        },
        {
          title: 'अधिकृत कागदपत्रांतून उत्तर',
          desc: 'उत्तर शासनाच्या अधिकृत योजना कागदपत्रांवर आधारित असते आणि सोबत कागदपत्राचे नाव व पान क्रमांक दिला जातो.'
        },
        {
          title: 'मूळ कागदपत्र तपासा',
          desc: 'हा सहाय्यक चुकू शकतो. अर्ज करण्यापूर्वी किंवा निर्णय घेण्यापूर्वी दिलेले पान तपासा, किंवा जवळच्या कृषी कार्यालयात खात्री करा.'
        }
      ],
      demoTitle: 'उदाहरण प्रश्न',
      demoSubtitle: 'उत्तर पाहण्यासाठी खालीलपैकी कोणत्याही प्रश्नावर क्लिक करा:',
      askButton: 'हा प्रश्न विचारा',
      sampleQueries: [
        { tag: 'वऱ्हाडी बोली', query: VARHADI_LOAN_QUERY, meaning: 'शेतकरी कर्जमाफी आणि शासकीय अनुदानाचा लाभ कसा मिळवता येईल?' },
        { tag: 'प्रमाण मराठी', query: NAMO_QUERY, meaning: 'नमो शेतकरी महासन्मान निधी योजनेची पात्रता व कागदपत्रे.' },
        { tag: 'पीक विमा', query: CROP_QUERY, meaning: 'अतिवृष्टीने कापूस व सोयाबीनचे नुकसान झाल्यास पीक विम्याची भरपाई कशी मागावी?' }
      ]
    },
    voice: {
      title: 'आवाज सहाय्यक',
      subtitle: 'माईक दाबून वऱ्हाडी किंवा मराठीत बोला, किंवा रेकॉर्ड केलेली ऑडिओ फाईल निवडा.',
      recordStart: 'बोला',
      recordStop: 'थांबवा',
      recordingTime: 'रेकॉर्डिंग वेळ',
      recordingLength: 'रेकॉर्डिंगची लांबी',
      uploadAudio: 'ऑडिओ फाईल निवडा',
      processing: 'तुमचा आवाज ऐकत आहे...',
      previewTitle: 'तुम्ही विचारलेला प्रश्न',
      yourRecording: 'तुमचे रेकॉर्डिंग',
      editTranscript: 'हा मजकूर बरोबर आहे का? गरज असल्यास दुरुस्त करा',
      understoodAs: 'प्रमाण मराठीत तुमचा प्रश्न',
      saveEdit: 'पुन्हा तपासा',
      submitToChat: 'या प्रश्नाचे उत्तर मिळवा',
      uncertainNotice: 'तुमचा आवाज कदाचित नीट ऐकू आला नाही. खालील मजकूर तपासून दुरुस्त करा, किंवा पुन्हा बोला.',
      noAudioRecorded: 'आवाज ओळखता आला नाही. कृपया पुन्हा बोला किंवा प्रश्न टाइप करा.',
      requestFailed: 'सध्या तुमचे रेकॉर्डिंग तपासता आले नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा किंवा प्रश्न टाइप करा.',
      micPermissionError: 'मायक्रोफोन परवानगी नाकारली किंवा मायक्रोफोन उपलब्ध नाही.'
    },
    chat: {
      title: 'शासकीय योजनांबद्दल विचारा',
      subtitle: 'उत्तरे अधिकृत शासकीय कागदपत्रांवर आधारित, कागदपत्राचे नाव व पान क्रमांकासह.',
      inputPlaceholder: 'तुमचा प्रश्न येथे मराठी किंवा वऱ्हाडीत टाइप करा (उदा. कर्जमाफीची पात्रता काय आहे?)...',
      sendButton: 'पाठवा',
      thinking: 'शासकीय कागदपत्रे तपासून उत्तर तयार करत आहे...',
      sourcesTitle: 'संदर्भ: शासकीय कागदपत्रे व पान क्रमांक',
      page: 'पान',
      viewEnglish: 'इंग्रजीत पहा',
      translating: 'इंग्रजीत भाषांतर होत आहे...',
      englishLabel: 'इंग्रजी भाषांतर',
      audioListen: 'मराठीत उत्तर ऐका',
      dialectBadge: 'बोलीभाषा',
      ratePrompt: 'हे उत्तर उपयुक्त आणि अचूक होते का?',
      rateCorrectionPlaceholder: 'काही त्रुटी किंवा सुधारणा असल्यास येथे लिहा...',
      submitFeedback: 'अभिप्राय पाठवा',
      feedbackThanks: 'धन्यवाद!',
      emptyChatPrompt: 'तुमचा प्रश्न खाली मराठी, वऱ्हाडी, हिंदी किंवा इंग्रजीत लिहा.',
      errorAnswer: 'माफ करा, सध्या उत्तर देता आले नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा.',
      actionFailed: 'काहीतरी चुकले. कृपया पुन्हा प्रयत्न करा.',
      checkSource: 'निर्णय घेण्यापूर्वी दिलेले मूळ पान तपासा.'
    },
    docs: {
      title: 'शासकीय कागदपत्रे',
      subtitle: 'सहाय्यक खालील अधिकृत कागदपत्रांवरून उत्तरे देतो. प्रत्येक कागदपत्राची मूळ प्रत शासनाच्या संकेतस्थळावर पाहता येते.',
      countLabel: 'कागदपत्रे',
      grNumber: 'शासन निर्णय क्र.',
      issued: 'दिनांक',
      openOfficial: 'मूळ प्रत उघडा',
      superseded: 'नव्या शासन निर्णयाने बदलले',
      emptyList: 'सध्या कोणतेही कागदपत्र उपलब्ध नाही.',
      loadError: 'कागदपत्रांची यादी आणता आली नाही. कृपया पुन्हा प्रयत्न करा.'
    },
    dialects: {
      standard: 'प्रमाण मराठी',
      varhadi: 'वऱ्हाडी (विदर्भ)'
    },
    footer: {
      text: '© २०२६ BharatLangTech AI — शासकीय योजनांसाठी बोलीभाषा जाणणारा मराठी सहाय्यक. उत्तरे अधिकृत कागदपत्रांवर आधारित आहेत; कृपया संदर्भित मूळ दस्तऐवज तपासा.'
    }
  },

  // 2. Varhadi (वऱ्हाडी बोली - विदर्भ)
  'mr-varhadi': {
    nav: {
      home: 'घर',
      voice: 'बोलून इचारा',
      chat: 'लिहून इचारा',
      docs: 'सरकारी कागदपत्रे',
      manageDocs: 'कागदपत्र व्यवस्थापन',
      qualityChecks: 'गुणवत्ता तपासणी',
      dialectBadge: 'वऱ्हाडी बोली',
      tagline: 'विदर्भातील शेतकरी बांधवांसाठी आपल्या बोलीतला सहाय्यक'
    },
    status: {
      checking: 'सेवा तपासणं चालू हाय…',
      available: 'सेवा चालू हाय',
      unavailable: 'सेवा थोडा वेळ बंद हाय',
      unavailableHint: 'आत्ता उत्तर द्यायला अडचण येऊन रायली, उत्तर अधुरं असू शकते. थोड्या वेळानं पुन्हा इचारा.'
    },
    home: {
      badge: 'सरकारी जीआरमधूनच उत्तर • पान नंबरसह',
      title: 'BharatLangTech AI',
      subtitle: 'आपल्या वऱ्हाडी बोलीभाषेत शेती आणि सरकारी योजनांची खरी माहिती',
      description: 'विदर्भातील शेतकरी भावांसाठी वऱ्हाडी अन् मराठीत. नमो शेतकरी, पीएम-किसान, पीक विमा अन् कर्जमुक्तीबद्दल इचारा; उत्तर सरकारी जीआर तपासूनच भेटन.',
      btnVoice: 'माईकमध्ये बोलून इचारा',
      btnChat: 'टाइप करून इचारा',
      btnDocs: 'सरकारी कागदपत्रे पहा',
      howTitle: 'हे कसं चालते',
      steps: [
        {
          title: 'बोलून नाहीतर लिहून इचारा',
          desc: 'वऱ्हाडी, मराठी, हिंदी नाहीतर इंग्रजीत इचारा. बोललेला प्रश्न आधी लिहिलेला दिसते; चुकला तर दुरुस्त करा.'
        },
        {
          title: 'सरकारी कागदपत्रातूनच उत्तर',
          desc: 'उत्तर सरकारी योजनांच्या अधिकृत कागदपत्रांवरून भेटते, सोबत कागदपत्राचं नाव अन् पान नंबर.'
        },
        {
          title: 'मूळ कागद एकदा पाहा',
          desc: 'हा सहाय्यक चुकू शकते. अर्ज करण्याआधी दिलेलं पान पाहा, नाहीतर जवळच्या कृषी कार्यालयात इचारून घ्या.'
        }
      ],
      demoTitle: 'शेतकरी भावांनी इचारलेले प्रश्न',
      demoSubtitle: 'कोणत्याही प्रश्नावर टिचकी मारा, पुराव्यासह उत्तर भेटन:',
      askButton: 'हा प्रश्न इचारा',
      sampleQueries: [
        { tag: 'वऱ्हाडी बोली', query: VARHADI_LOAN_QUERY, meaning: 'कर्जमाफी आणि अनुदानाचे पैसे कसे मिळवायचे?' },
        { tag: 'नमो शेतकरी योजना', query: 'नमो शेतकरी महासन्मान निधीचे पैसे कोणले भेटतात अन् काय कागद लागतात?', meaning: 'नमो शेतकरी योजनेची पात्रता व आवश्यक कागदपत्रे.' },
        { tag: 'पीक विमा', query: 'अतिवृष्टीने सोयाबीन आणि कापूस नासून गेला, विमा कंपनीले तक्रार कशी द्यायची?', meaning: 'अतिवृष्टीनं पिकाचं नुकसान झालं तर पीक विम्याची भरपाई कशी मागायची?' }
      ]
    },
    voice: {
      title: 'बोलून प्रश्न इचारा',
      subtitle: 'आपल्या वऱ्हाडी बोलीत बोला, माईक दाबा अन् इचारा.',
      recordStart: 'बोला',
      recordStop: 'थांबवा',
      recordingTime: 'बोलण्याची वेळ',
      recordingLength: 'रेकॉर्डिंगची लांबी',
      uploadAudio: 'रेकॉर्डिंग फाईल निवडा',
      processing: 'तुमचा आवाज ऐकणे चालू हाय...',
      previewTitle: 'तुम्ही इचारलेला प्रश्न',
      yourRecording: 'तुमचं रेकॉर्डिंग',
      editTranscript: 'हे बरोबर हाय का? चुकलं असन तर दुरुस्त करा',
      understoodAs: 'प्रमाण मराठीत तुमचा प्रश्न',
      saveEdit: 'पुन्हा तपासा',
      submitToChat: 'या प्रश्नाचे उत्तर काढा',
      uncertainNotice: 'तुमचा आवाज नीट ऐकू आला नसन. खालचं लिहिलेलं तपासा, नाहीतर पुन्हा बोला.',
      noAudioRecorded: 'आवाज ओळखता आला नाही. पुन्हा बोला नाहीतर प्रश्न टाइप करा.',
      requestFailed: 'आत्ता तुमचं रेकॉर्डिंग तपासता आलं नाही. थोड्या वेळानं पुन्हा प्रयत्न करा नाहीतर प्रश्न टाइप करा.',
      micPermissionError: 'मायक्रोफोन चालू करायची परवानगी द्यावी लागेल.'
    },
    chat: {
      title: 'योजनांची माहिती इचारा',
      subtitle: 'सरकारी जीआर तपासून दिलेल्या पानांच्या पुराव्यासह उत्तर.',
      inputPlaceholder: 'तुमचा प्रश्न इथं लिहा (उदा. मले २ लाख कर्जमाफी कशी भेटन?)...',
      sendButton: 'पाठवा',
      thinking: 'सरकारी कागदपत्रे तपासून उत्तर तयार करत हाय...',
      sourcesTitle: 'पुरावा: सरकारी कागदपत्रे अन् पान नंबर',
      page: 'पान',
      viewEnglish: 'इंग्रजीत पहा',
      translating: 'इंग्रजीत भाषांतर होत हाय...',
      englishLabel: 'इंग्रजी भाषांतर',
      audioListen: 'मराठीत उत्तर ऐका',
      dialectBadge: 'बोलीभाषा',
      ratePrompt: 'हे उत्तर बरोबर हाय का?',
      rateCorrectionPlaceholder: 'काही चूक वाटल्यास इथं लिहा...',
      submitFeedback: 'अभिप्राय द्या',
      feedbackThanks: 'धन्यवाद!',
      emptyChatPrompt: 'तुमचा प्रश्न खाली लिहा: वऱ्हाडी, मराठी, हिंदी नाहीतर इंग्रजीत.',
      errorAnswer: 'माफ करा, आत्ता उत्तर देता आलं नाही. थोड्या वेळानं पुन्हा इचारा.',
      actionFailed: 'काहीतरी चुकलं. पुन्हा प्रयत्न करा.',
      checkSource: 'निर्णय घेण्याआधी मूळ पान एकदा पाहा.'
    },
    docs: {
      title: 'सरकारी कागदपत्रे',
      subtitle: 'सहाय्यक या सरकारी कागदपत्रांवरूनच उत्तर देते. प्रत्येकाची मूळ प्रत सरकारच्या वेबसाईटवर पाहता येते.',
      countLabel: 'कागदपत्रे',
      grNumber: 'शासन निर्णय क्र.',
      issued: 'तारीख',
      openOfficial: 'मूळ प्रत उघडा',
      superseded: 'नव्या जीआरनं बदललेलं',
      emptyList: 'अजून एकही कागदपत्र नाही.',
      loadError: 'कागदपत्रांची यादी आणता आली नाही. पुन्हा प्रयत्न करा.'
    },
    dialects: {
      standard: 'प्रमाण मराठी',
      varhadi: 'वऱ्हाडी (विदर्भ)'
    },
    footer: {
      text: '© २०२६ BharatLangTech AI — विदर्भातील शेतकरी बांधवांसाठी आपल्या वऱ्हाडी बोलीतला सहाय्यक. उत्तर सरकारी कागदपत्रांवरून; मूळ कागद एकदा तपासून घ्या.'
    }
  },

  // 3. Hindi (हिंदी)
  hi: {
    nav: {
      home: 'मुख्य पृष्ठ',
      voice: 'आवाज़ सहायक',
      chat: 'संवाद',
      docs: 'सरकारी दस्तावेज़',
      manageDocs: 'दस्तावेज़ प्रबंधन',
      qualityChecks: 'गुणवत्ता जाँच',
      dialectBadge: 'बोलियाँ समझने वाला',
      tagline: 'स्थानीय भाषा व बोलीभाषा बहुभाषी सहायक'
    },
    status: {
      checking: 'सेवा की जाँच हो रही है…',
      available: 'सेवा उपलब्ध',
      unavailable: 'सेवा अस्थायी रूप से अनुपलब्ध',
      unavailableHint: 'अभी उत्तर देने में समस्या आ रही है, इसलिए उत्तर अधूरे हो सकते हैं। कृपया थोड़ी देर बाद फिर प्रयास करें।'
    },
    home: {
      badge: 'आधिकारिक सरकारी दस्तावेज़ों से, पृष्ठ संख्या सहित उत्तर',
      title: 'BharatLangTech AI',
      subtitle: 'स्थानीय भाषा और बोलियों को समझने वाला बहुभाषी कृषि व सरकारी योजना सहायक',
      description: 'विदर्भ की वऱ्हाडी और मानक मराठी बोलने वाले किसानों के लिए। नमो शेतकरी, पीएम-किसान, फसल बीमा और कर्जमुक्ति योजनाओं के बारे में पूछें; उत्तर महाराष्ट्र सरकार के आधिकारिक शासन निर्णयों पर आधारित होते हैं।',
      btnVoice: 'बोलकर पूछें',
      btnChat: 'टाइप करके पूछें',
      btnDocs: 'सरकारी दस्तावेज़ देखें',
      howTitle: 'यह कैसे काम करता है',
      steps: [
        {
          title: 'बोलकर या टाइप करके पूछें',
          desc: 'मराठी, वऱ्हाडी, हिंदी या अंग्रेज़ी में पूछें। बोला गया प्रश्न पहले लिखा हुआ दिखता है; ज़रूरत हो तो उसे सुधारें।'
        },
        {
          title: 'आधिकारिक दस्तावेज़ों से उत्तर',
          desc: 'उत्तर सरकारी योजनाओं के आधिकारिक दस्तावेज़ों पर आधारित होता है, साथ में दस्तावेज़ का नाम और पृष्ठ संख्या दी जाती है।'
        },
        {
          title: 'मूल दस्तावेज़ जाँचें',
          desc: 'यह सहायक गलती कर सकता है। आवेदन या निर्णय से पहले दिया गया पृष्ठ जाँचें, या नज़दीकी कृषि कार्यालय से पुष्टि करें।'
        }
      ],
      demoTitle: 'उदाहरण प्रश्न',
      demoSubtitle: 'उत्तर देखने के लिए नीचे किसी भी प्रश्न पर क्लिक करें:',
      askButton: 'यह प्रश्न पूछें',
      sampleQueries: [
        { tag: 'वऱ्हाडी बोली', query: VARHADI_LOAN_QUERY, meaning: 'किसानों के लिए ऋण माफ़ी और सरकारी अनुदान का लाभ कैसे प्राप्त करें?' },
        { tag: 'मानक मराठी', query: NAMO_QUERY, meaning: 'नमो शेतकरी महासन्मान निधि योजना के पात्रता मानदंड और आवश्यक दस्तावेज़।' },
        { tag: 'फसल बीमा', query: CROP_QUERY, meaning: 'भारी बारिश से कपास और सोयाबीन की फसल खराब होने पर फसल बीमा मुआवज़ा कैसे माँगें?' }
      ]
    },
    voice: {
      title: 'आवाज़ सहायक',
      subtitle: 'माइक दबाकर वऱ्हाडी या मराठी में बोलें, या रिकॉर्ड की हुई ऑडियो फ़ाइल चुनें।',
      recordStart: 'बोलें',
      recordStop: 'रोकें',
      recordingTime: 'रिकॉर्डिंग समय',
      recordingLength: 'रिकॉर्डिंग की लंबाई',
      uploadAudio: 'ऑडियो फ़ाइल चुनें',
      processing: 'आपकी आवाज़ सुनी जा रही है...',
      previewTitle: 'आपका पूछा गया प्रश्न',
      yourRecording: 'आपकी रिकॉर्डिंग',
      editTranscript: 'क्या यह सही है? ज़रूरत हो तो सुधारें',
      understoodAs: 'मानक मराठी में आपका प्रश्न',
      saveEdit: 'फिर से जाँचें',
      submitToChat: 'इस प्रश्न का उत्तर पाएँ',
      uncertainNotice: 'शायद आपकी आवाज़ साफ़ सुनाई नहीं दी। नीचे लिखा पाठ जाँचकर सुधारें, या फिर से बोलें।',
      noAudioRecorded: 'आवाज़ पहचानी नहीं जा सकी। कृपया फिर से बोलें या प्रश्न टाइप करें।',
      requestFailed: 'अभी आपकी रिकॉर्डिंग जाँची नहीं जा सकी। कृपया थोड़ी देर बाद फिर प्रयास करें या प्रश्न टाइप करें।',
      micPermissionError: 'माइक्रोफ़ोन अनुमति अस्वीकृत या माइक्रोफ़ोन अनुपलब्ध।'
    },
    chat: {
      title: 'सरकारी योजनाओं के बारे में पूछें',
      subtitle: 'उत्तर आधिकारिक सरकारी दस्तावेज़ों पर आधारित, दस्तावेज़ के नाम और पृष्ठ संख्या सहित।',
      inputPlaceholder: 'अपना प्रश्न यहाँ टाइप करें (उदा. ऋण माफ़ी की पात्रता क्या है?)...',
      sendButton: 'भेजें',
      thinking: 'सरकारी दस्तावेज़ों की जाँच कर उत्तर तैयार किया जा रहा है...',
      sourcesTitle: 'संदर्भ: सरकारी दस्तावेज़ और पृष्ठ संख्या',
      page: 'पृष्ठ',
      viewEnglish: 'अंग्रेज़ी में देखें',
      translating: 'अंग्रेज़ी में अनुवाद हो रहा है...',
      englishLabel: 'अंग्रेज़ी अनुवाद',
      audioListen: 'मराठी में उत्तर सुनें',
      dialectBadge: 'बोली',
      ratePrompt: 'क्या यह उत्तर उपयोगी और सटीक था?',
      rateCorrectionPlaceholder: 'यदि कोई त्रुटि या सुधार हो तो यहाँ लिखें...',
      submitFeedback: 'प्रतिक्रिया भेजें',
      feedbackThanks: 'धन्यवाद!',
      emptyChatPrompt: 'अपना प्रश्न नीचे मराठी, वऱ्हाडी, हिंदी या अंग्रेज़ी में लिखें।',
      errorAnswer: 'क्षमा करें, अभी उत्तर नहीं दिया जा सका। कृपया थोड़ी देर बाद फिर प्रयास करें।',
      actionFailed: 'कुछ गड़बड़ हो गई। कृपया फिर प्रयास करें।',
      checkSource: 'निर्णय लेने से पहले दिया गया मूल पृष्ठ जाँचें।'
    },
    docs: {
      title: 'सरकारी दस्तावेज़',
      subtitle: 'सहायक नीचे दिए गए आधिकारिक दस्तावेज़ों से उत्तर देता है। हर दस्तावेज़ की मूल प्रति सरकारी वेबसाइट पर देखी जा सकती है।',
      countLabel: 'दस्तावेज़',
      grNumber: 'शासन निर्णय क्र.',
      issued: 'दिनांक',
      openOfficial: 'मूल प्रति खोलें',
      superseded: 'नए आदेश द्वारा बदला गया',
      emptyList: 'अभी कोई दस्तावेज़ उपलब्ध नहीं है।',
      loadError: 'दस्तावेज़ों की सूची नहीं मिल सकी। कृपया फिर प्रयास करें।'
    },
    dialects: {
      standard: 'मानक मराठी',
      varhadi: 'वऱ्हाडी (विदर्भ)'
    },
    footer: {
      text: '© 2026 BharatLangTech AI — सरकारी योजनाओं के लिए बोलियाँ समझने वाला मराठी सहायक। उत्तर आधिकारिक दस्तावेज़ों पर आधारित हैं; कृपया संदर्भित मूल दस्तावेज़ जाँचें।'
    }
  },

  // 4. English
  en: {
    nav: {
      home: 'Home',
      voice: 'Voice Assistant',
      chat: 'Text Chat',
      docs: 'Government Documents',
      manageDocs: 'Manage documents',
      qualityChecks: 'Quality checks',
      dialectBadge: 'Dialect-Aware',
      tagline: 'Marathi and Varhadi assistant for farmer schemes'
    },
    status: {
      checking: 'Checking service…',
      available: 'Service available',
      unavailable: 'Service temporarily unavailable',
      unavailableHint: 'The assistant is having trouble right now, so answers may be incomplete. Please try again in a little while.'
    },
    home: {
      badge: 'Answers from official government documents, with page numbers',
      title: 'BharatLangTech AI',
      subtitle: 'A farm and government scheme assistant that understands Marathi and Varhadi',
      description: 'For farmers in Vidarbha who speak Varhadi or standard Marathi. Ask about Namo Shetkari, PM-KISAN, crop insurance and the loan waiver; answers are based on official Maharashtra government resolutions.',
      btnVoice: 'Ask by voice',
      btnChat: 'Type a question',
      btnDocs: 'See the documents',
      howTitle: 'How it works',
      steps: [
        {
          title: 'Ask by voice or by typing',
          desc: 'Ask in Marathi, Varhadi, Hindi or English. A spoken question is shown as text first, so you can check and correct it.'
        },
        {
          title: 'Answers from official documents',
          desc: 'Answers are based on official government scheme documents and name the document and page they come from.'
        },
        {
          title: 'Check the original',
          desc: 'This assistant can make mistakes. Before you apply or decide, check the cited page, or confirm at your nearest agriculture office.'
        }
      ],
      demoTitle: 'Example questions',
      demoSubtitle: 'Click a question below to see the answer:',
      askButton: 'Ask this question',
      sampleQueries: [
        { tag: 'Varhadi (Vidarbha)', query: VARHADI_LOAN_QUERY, meaning: 'How can I get the farm loan waiver and government subsidies?' },
        { tag: 'Standard Marathi', query: NAMO_QUERY, meaning: 'Who is eligible for Namo Shetkari Mahasanman Nidhi, and which documents are needed?' },
        { tag: 'Crop insurance', query: CROP_QUERY, meaning: 'How do I claim crop insurance for heavy-rain damage to cotton and soybean?' }
      ]
    },
    voice: {
      title: 'Voice Assistant',
      subtitle: 'Press the microphone and speak in Varhadi or Marathi, or choose a recorded audio file.',
      recordStart: 'Speak',
      recordStop: 'Stop',
      recordingTime: 'Recording time',
      recordingLength: 'Recording length',
      uploadAudio: 'Choose an audio file',
      processing: 'Listening to your recording...',
      previewTitle: 'Your question',
      yourRecording: 'Your recording',
      editTranscript: 'Is this right? Correct it if needed',
      understoodAs: 'Your question in standard Marathi',
      saveEdit: 'Check again',
      submitToChat: 'Get the answer',
      uncertainNotice: 'We may not have heard you clearly. Check the text below and correct it, or record again.',
      noAudioRecorded: 'Your voice could not be recognised. Please speak again or type your question.',
      requestFailed: 'Your recording could not be checked right now. Please try again in a little while, or type your question.',
      micPermissionError: 'Microphone access was denied, or no microphone is available.'
    },
    chat: {
      title: 'Ask about government schemes',
      subtitle: 'Answers are based on official government documents, with the document name and page number.',
      inputPlaceholder: 'Type your question in Marathi, Varhadi, Hindi or English (e.g. who is eligible for the loan waiver?)...',
      sendButton: 'Send',
      thinking: 'Checking the government documents and preparing an answer...',
      sourcesTitle: 'Sources: government documents and pages',
      page: 'Page',
      viewEnglish: 'View in English',
      translating: 'Translating to English...',
      englishLabel: 'English translation',
      audioListen: 'Listen to the answer in Marathi',
      dialectBadge: 'Dialect',
      ratePrompt: 'Was this answer helpful and accurate?',
      rateCorrectionPlaceholder: 'Suggest corrections or missing details here...',
      submitFeedback: 'Send feedback',
      feedbackThanks: 'Thank you!',
      emptyChatPrompt: 'Type your question below in Marathi, Varhadi, Hindi or English.',
      errorAnswer: 'Sorry, we could not answer right now. Please try again in a little while.',
      actionFailed: 'Something went wrong. Please try again.',
      checkSource: 'Check the original page before you decide.'
    },
    docs: {
      title: 'Government Documents',
      subtitle: 'The assistant answers from the official documents below. The original of each one can be opened on the government website.',
      countLabel: 'Documents',
      grNumber: 'Government Resolution No.',
      issued: 'Dated',
      openOfficial: 'Open the original',
      superseded: 'Replaced by a newer order',
      emptyList: 'No documents are available right now.',
      loadError: 'The document list could not be loaded. Please try again.'
    },
    dialects: {
      standard: 'Standard Marathi',
      varhadi: 'Varhadi (Vidarbha)'
    },
    footer: {
      text: '© 2026 BharatLangTech AI — Dialect-aware Marathi assistant for government schemes. Answers come from official documents; always check the cited source.'
    }
  }
};

export const getTranslation = (lang: string): TranslationDictionary => {
  return translations[lang] || translations.mr;
};
