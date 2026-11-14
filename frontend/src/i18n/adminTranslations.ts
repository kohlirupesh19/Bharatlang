// Operator-only strings (document management and quality checks). Imported only by the
// lazily loaded admin screens, so none of these technical terms ship in the citizen bundle.
export interface AdminTranslationDictionary {
  kb: {
    title: string;
    subtitle: string;
    uploadHeader: string;
    fileLabel: string;
    titleLabel: string;
    authorityLabel: string;
    uploadBtn: string;
    uploading: string;
    statsTotalDocs: string;
    statsTotalChunks: string;
    indexedListHeader: string;
    docDelete: string;
    rebuildBtn: string;
    rebuilding: string;
    emptyList: string;
  };
  eval: {
    title: string;
    subtitle: string;
    btnRunAsr: string;
    btnRunRag: string;
    runningAsr: string;
    runningRag: string;
    asrSectionTitle: string;
    modelSelectLabel: string;
    werLabel: string;
    werDesc: string;
    cerLabel: string;
    cerDesc: string;
    exactMatchLabel: string;
    exactMatchDesc: string;
    latencyLabel: string;
    latencyDesc: string;
    categoryBreakdownTitle: string;
    samplesCount: string;
    ragSectionTitle: string;
    recallLabel: string;
    recallDesc: string;
    precisionLabel: string;
    precisionDesc: string;
    mrrLabel: string;
    mrrDesc: string;
    suppressionLabel: string;
    suppressionDesc: string;
    noDataTitle: string;
    noDataDesc: string;
  };
}

export const adminTranslations: Record<string, AdminTranslationDictionary> = {
  mr: {
    kb: {
      title: 'शासकीय कागदपत्रे ज्ञान भांडार (Knowledge Base)',
      subtitle: 'महाराष्ट्र शासनाचे अधिकृत जीआर व परिपत्रके अपलोड करा. PyMuPDF आणि Tesseract OCR द्वारे थेट इंडेक्सिंग.',
      uploadHeader: 'नवीन शासकीय अध्यादेश / जीआर (PDF) अपलोड करा',
      fileLabel: 'PDF फाईल निवडा',
      titleLabel: 'योजनेचे नाव / कागदपत्राचे शीर्षक',
      authorityLabel: 'निर्गमित विभाग / प्राधिकरण',
      uploadBtn: 'कागदपत्र प्रोसेस व इंडेक्स करा',
      uploading: 'दस्तऐवज स्कॅनिंग व OCR प्रक्रिया चालू आहे...',
      statsTotalDocs: 'एकूण कागदपत्रे',
      statsTotalChunks: 'इंडेक्स केलेले परिच्छेद',
      indexedListHeader: 'ज्ञान भांडारातील उपलब्ध शासकीय दस्तऐवज',
      docDelete: 'हटवा',
      rebuildBtn: 'इंडेक्स पुन्हा तयार करा',
      rebuilding: 'पुन्हा इंडेक्स करत आहे...',
      emptyList: 'कोणतेही कागदपत्र अपलोड केलेले नाही.'
    },
    eval: {
      title: 'मूल्यांकन व अचूकता डॅशबोर्ड (Evaluation Dashboard)',
      subtitle: 'मानव-सत्यापित संदर्भ संचावर आधारित प्रत्यक्ष मोजलेली अचूकता आकडेवारी (Zero Fabricated Metrics).',
      btnRunAsr: 'ASR चाचणी चालवा',
      btnRunRag: 'RAG बेंचमार्क चालवा',
      runningAsr: 'ASR चाचणी चालू...',
      runningRag: '३० प्रश्नांची चाचणी चालू...',
      asrSectionTitle: 'ध्वनी ओळख मूल्यमापन (Speech Recognition - WER & CER)',
      modelSelectLabel: 'मॉडेल निवडा:',
      werLabel: 'Word Error Rate (WER)',
      werDesc: 'शब्दांमधील त्रुटीचे प्रमाण (कमी तितके चांगले)',
      cerLabel: 'Character Error Rate (CER)',
      cerDesc: 'अक्षरांमधील त्रुटीचे प्रमाण',
      exactMatchLabel: 'अचूक जुळणी (Exact Match)',
      exactMatchDesc: '१००% अचूक वाक्ये',
      latencyLabel: 'सरासरी वेळ (Latency)',
      latencyDesc: 'प्रति वाक्य प्रक्रियेची वेळ',
      categoryBreakdownTitle: 'बोलीभाषा वर्गीकरण विश्लेषण (Dialect-Specific Breakdown)',
      samplesCount: 'चाचणी वाक्ये',
      ragSectionTitle: 'शासकीय योजना शोध अचूकता (RAG Retrieval - 30 Question Benchmark)',
      recallLabel: 'Recall @ Top 4',
      recallDesc: 'अपेक्षित माहिती सापडण्याचे प्रमाण',
      precisionLabel: 'Precision @ Top 4',
      precisionDesc: 'शोधलेल्या उताऱ्यांची सुसंगतता',
      mrrLabel: 'Mean Reciprocal Rank (MRR)',
      mrrDesc: 'पहिल्या योग्य परिच्छेदाची क्रमवारी',
      suppressionLabel: 'अप्रासंगिक प्रश्न रोखणे',
      suppressionDesc: 'काल्पनिक माहिती न देण्याचे प्रमाण',
      noDataTitle: 'कोणतीही चाचणी आकडेवारी उपलब्ध नाही',
      noDataDesc: 'प्रत्यक्ष मॉडेल तपासण्यासाठी वरील "बेंचमार्क चालवा" बटण दाबा.'
    }
  },
  'mr-varhadi': {
    kb: {
      title: 'सरकारी जीआर कागदपत्रे (Knowledge Base)',
      subtitle: 'सरकारी शासन निर्णय (PDF) अपलोड करा, सिस्टिम थेट वाचून इंडेक्स करेल.',
      uploadHeader: 'नवीन जीआर (PDF) टाका',
      fileLabel: 'PDF फाईल निवडा',
      titleLabel: 'कागदपत्राचे नाव',
      authorityLabel: 'विभाग',
      uploadBtn: 'कागदपत्र जोडा व इंडेक्स करा',
      uploading: 'कागदपत्र वाचणे चालू हाय...',
      statsTotalDocs: 'एकूण कागदपत्रे',
      statsTotalChunks: 'तपासलेले परिच्छेद',
      indexedListHeader: 'सिस्टिममध्ये जमा असलेले कागदपत्रे',
      docDelete: 'काढून टाका',
      rebuildBtn: 'पुन्हा तपासा',
      rebuilding: 'पुन्हा तपासणे चालू हाय...',
      emptyList: 'अजून एकही कागदपत्र जोडलेलं नाही.'
    },
    eval: {
      title: 'अचूकता तपासणी डॅशबोर्ड (Evaluation Dashboard)',
      subtitle: 'आपल्या वऱ्हाडी आणि प्रमाण मराठीतील खरीखुरी मोजलेली अचूकता.',
      btnRunAsr: 'ASR चाचणी घ्या',
      btnRunRag: 'RAG चाचणी घ्या',
      runningAsr: 'ASR तपासणी चालू हाय...',
      runningRag: '३० प्रश्नांची तपासणी चालू...',
      asrSectionTitle: 'आवाज ओळख चाचणी (WER व CER)',
      modelSelectLabel: 'मॉडेल निवडा:',
      werLabel: 'शब्दांमधील चूक (WER)',
      werDesc: 'कमी चूक म्हणजे जास्त चांगलं',
      cerLabel: 'अक्षरांमधील चूक (CER)',
      cerDesc: 'अक्षरांचे अचूक प्रमाण',
      exactMatchLabel: '१००% तंतोतंत जुळणी',
      exactMatchDesc: 'जसेच्या तसे बरोबर वाक्ये',
      latencyLabel: 'सरासरी वेळ',
      latencyDesc: 'एका वाक्याला लागणारा वेळ',
      categoryBreakdownTitle: 'बोलीनुसार अचूकता विश्लेषण',
      samplesCount: 'चाचणी वाक्ये',
      ragSectionTitle: 'सरकारी माहिती शोध अचूकता (RAG 30 Benchmark)',
      recallLabel: 'माहिती सापडणे (Recall)',
      recallDesc: 'अपेक्षित पुरावा सापडण्याचे प्रमाण',
      precisionLabel: 'योग्य परिच्छेद (Precision)',
      precisionDesc: 'शोधलेल्या भागांची सुसंगतता',
      mrrLabel: 'पहिले योग्य पान (MRR)',
      mrrDesc: 'पहिल्या प्रयत्नात योग्य संदर्भ मिळणे',
      suppressionLabel: 'खोट्या गोष्टी रोखणे',
      suppressionDesc: 'माहिती नसताना खोटं न बोलण्याचे प्रमाण',
      noDataTitle: 'अजून चाचणी घेतलेली नाही',
      noDataDesc: 'तपासणी करण्यासाठी वरील बटण दाबा.'
    }
  },
  hi: {
    kb: {
      title: 'सरकारी दस्तावेज़ ज्ञान भंडार (Knowledge Base)',
      subtitle: 'महाराष्ट्र शासन के आधिकारिक आदेश (GR) अपलोड करें। PyMuPDF और Tesseract OCR द्वारा अनुक्रमण।',
      uploadHeader: 'नया सरकारी आदेश (PDF) अपलोड करें',
      fileLabel: 'PDF फ़ाइल चुनें',
      titleLabel: 'योजना का नाम / दस्तावेज़ शीर्षक',
      authorityLabel: 'जारीकर्ता विभाग / प्राधिकरण',
      uploadBtn: 'दस्तावेज़ प्रोसेस और इंडेक्स करें',
      uploading: 'दस्तावेज़ स्कैनिंग और OCR प्रक्रिया जारी है...',
      statsTotalDocs: 'कुल दस्तावेज़',
      statsTotalChunks: 'इंडेक्स किए गए पैराग्राफ',
      indexedListHeader: 'उपलब्ध सरकारी दस्तावेज़',
      docDelete: 'हटाएं',
      rebuildBtn: 'इंडेक्स पुनः बनाएं',
      rebuilding: 'पुनः इंडेक्सिंग जारी है...',
      emptyList: 'अभी तक कोई दस्तावेज़ अपलोड नहीं किया गया है।'
    },
    eval: {
      title: 'मूल्यांकन और सटीकता डैशबोर्ड (Evaluation Dashboard)',
      subtitle: 'मानव-सत्यापित संदर्भ सेट पर आधारित वास्तविक सटीकता आंकड़े (Zero Fabricated Metrics).',
      btnRunAsr: 'ASR बेंचमार्क चलाएं',
      btnRunRag: 'RAG बेंचमार्क चलाएं',
      runningAsr: 'ASR परीक्षण जारी...',
      runningRag: '30 प्रश्नों की जांच जारी...',
      asrSectionTitle: 'ध्वनि पहचान मूल्यांकन (Speech Recognition - WER & CER)',
      modelSelectLabel: 'मॉडल चुनें:',
      werLabel: 'Word Error Rate (WER)',
      werDesc: 'शब्द स्तर पर त्रुटि अनुपात (कम होना बेहतर)',
      cerLabel: 'Character Error Rate (CER)',
      cerDesc: 'अक्षर स्तर पर त्रुटि अनुपात',
      exactMatchLabel: 'सटीक मिलान (Exact Match)',
      exactMatchDesc: '100% सटीक वाक्य',
      latencyLabel: 'औसत समय (Latency)',
      latencyDesc: 'प्रति वाक्य प्रसंस्करण समय',
      categoryBreakdownTitle: 'बोली-विशिष्ट सटीकता विश्लेषण',
      samplesCount: 'परीक्षण वाक्य',
      ragSectionTitle: 'सरकारी योजना खोज सटीकता (RAG 30 Question Benchmark)',
      recallLabel: 'Recall @ Top 4',
      recallDesc: 'अपेक्षित जानकारी मिलने की दर',
      precisionLabel: 'Precision @ Top 4',
      precisionDesc: 'खोजे गए अंशों की प्रासंगिकता',
      mrrLabel: 'Mean Reciprocal Rank (MRR)',
      mrrDesc: 'प्रथम प्रासंगिक उद्धरण की स्थिति',
      suppressionLabel: 'अप्रासंगिक प्रश्नों की रोकथाम',
      suppressionDesc: 'काल्पनिक उत्तर न देने की दर',
      noDataTitle: 'कोई परीक्षण डेटा उपलब्ध नहीं है',
      noDataDesc: 'वास्तविक मॉडल परीक्षण के लिए ऊपर "बेंचमार्क चलाएं" बटन दबाएं।'
    }
  },
  en: {
    kb: {
      title: 'Government Scheme Document Repository',
      subtitle: 'Upload official Maharashtra Government Resolutions (GRs). Processed with PyMuPDF & Tesseract OCR.',
      uploadHeader: 'Upload New Scheme Resolution (PDF)',
      fileLabel: 'Select PDF Document',
      titleLabel: 'Scheme / Document Title',
      authorityLabel: 'Issuing Department / Authority',
      uploadBtn: 'Process & Index Document',
      uploading: 'Scanning PDF & Extracting Text (OCR)...',
      statsTotalDocs: 'Total Documents',
      statsTotalChunks: 'Indexed Semantic Chunks',
      indexedListHeader: 'Indexed Government Resolutions in Knowledge Base',
      docDelete: 'Delete',
      rebuildBtn: 'Rebuild FAISS Index',
      rebuilding: 'Rebuilding Vector Index...',
      emptyList: 'No documents uploaded yet.'
    },
    eval: {
      title: 'Evaluation & Accuracy Benchmark Dashboard',
      subtitle: 'Empirical accuracy metrics measured on human-verified Marathi and Varhadi reference datasets (No Fabricated Metrics).',
      btnRunAsr: 'Run ASR Benchmark',
      btnRunRag: 'Run RAG Benchmark',
      runningAsr: 'Running Speech Benchmark...',
      runningRag: 'Evaluating 30 Questions...',
      asrSectionTitle: 'Speech Recognition Accuracy (WER & CER)',
      modelSelectLabel: 'Select Model:',
      werLabel: 'Word Error Rate (WER)',
      werDesc: 'Word level error rate (Lower is better)',
      cerLabel: 'Character Error Rate (CER)',
      cerDesc: 'Character level error rate',
      exactMatchLabel: 'Exact Match Rate',
      exactMatchDesc: '100% exact transcript matches',
      latencyLabel: 'Average Latency',
      latencyDesc: 'Processing time per sentence',
      categoryBreakdownTitle: 'Dialect-Specific Recognition Breakdown',
      samplesCount: 'Test Sentences',
      ragSectionTitle: 'Scheme Retrieval Accuracy (30-Question Benchmark)',
      recallLabel: 'Recall @ Top 4',
      recallDesc: 'Proportion of expected facts retrieved',
      precisionLabel: 'Precision @ Top 4',
      precisionDesc: 'Relevance of retrieved chunks',
      mrrLabel: 'Mean Reciprocal Rank (MRR)',
      mrrDesc: 'Position of first relevant citation',
      suppressionLabel: 'Unsupported Claim Suppression',
      suppressionDesc: 'Rejection of out-of-domain speculation',
      noDataTitle: 'No Benchmark Data Available',
      noDataDesc: 'Click "Run Benchmark" above to test the active models against verified ground truth.'
    }
  }
};

export const getAdminTranslation = (lang: string): AdminTranslationDictionary => {
  return adminTranslations[lang] || adminTranslations.mr;
};
