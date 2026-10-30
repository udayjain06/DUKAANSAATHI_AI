import React, { createContext, useContext, useState, useEffect } from 'react'

const LanguageContext = createContext(null)

export const translations = {
  en: {
    // Navigation
    dashboard: 'Dashboard',
    sales: 'Sales',
    products: 'Products',
    bills: 'Bills',
    recommendations: 'Suggestions',
    offers: 'Offers',
    margin: 'Margin',
    chat: 'AI Chat',
    payment: 'Plans',
    setup: 'Setup',
    login: 'Login',
    logout: 'Logout',
    getOffers: 'Get offers',
    
    // Dashboard & Hero
    merchantIntelligence: 'Merchant Intelligence & AI Analytics',
    heroTag: 'Spot slow days, price offers safely and grow your margin — all from your last 8 weeks of sales.',
    totalRevenue: 'Total Revenue · 8 Weeks',
    avgPerDay: 'Avg / day',
    salesAnalysis: 'Sales Analysis',
    weakDay: 'Weak Day',
    noneDetected: 'None detected',
    atAGlance: 'At a glance',
    yourShopInSimpleBlocks: 'Your shop, in simple blocks',
    numbersThatMatter: 'The numbers that matter, without the noise.',
    revenueTrend: '8-Week Revenue Trend',
    transactions: 'Transactions',
    bestDay: 'Best Day',
    worstDay: 'Worst Day',
    pendingActions: 'Pending Actions',
    review: 'Review →',
    
    // Dynamic Finance & ML
    userLedger: 'Personal Financial Hub & ML Engine',
    currentBalance: 'Wallet & Account Balance',
    monthlyIncome: 'Monthly Income',
    monthlyExpenses: 'Monthly Expenses',
    predictedSpending: 'Predicted 30-Day Spending',
    savingsRate: 'Savings Rate',
    spendingByCategory: 'Expense Breakdown by Category',
    recentTransactions: 'Recent Ledger Transactions',
    addTransaction: '+ Add Transaction',
    anomalyAlert: 'Unusual Transaction Alert',
    aiInsights: 'Personalized Financial Insights',
    modelConfidence: 'ML Model Confidence',
    
    // General
    syntheticNotice: '📊 Demo / Synthetic Data — Controlled calculations for demonstration.',
    loading: 'Loading...',
    save: 'Save',
    cancel: 'Cancel',
    amount: 'Amount',
    description: 'Description',
    category: 'Category',
    type: 'Type',
    date: 'Date',
    allRightsReserved: 'Paytm Build for India Hackathon',
  },
  hi: {
    // Navigation
    dashboard: 'डैशबोर्ड',
    sales: 'बिक्री विश्लेषण',
    products: 'उत्पाद व लागत',
    bills: 'बिल अपलोड',
    recommendations: 'सुझाव',
    offers: 'ऑफ़र व प्रयोग',
    margin: 'मार्जिन कैलकुलेटर',
    chat: 'AI सहायक',
    payment: 'सदस्यता प्लान',
    setup: 'दुकान सेटअप',
    login: 'लॉग इन',
    logout: 'लॉग आउट',
    getOffers: 'ऑफ़र देखें',
    
    // Dashboard & Hero
    merchantIntelligence: 'दुकानदार इंटेलिजेंस व AI एनालिटिक्स',
    heroTag: 'धीमे दिनों को पहचानें, सुरक्षित ऑफ़र बनाएं और अपना मुनाफ़ा बढ़ाएं—पिछले 8 हफ़्तों के डेटा से।',
    totalRevenue: 'कुल बिक्री · 8 हफ़्ते',
    avgPerDay: 'औसत / दिन',
    salesAnalysis: 'बिक्री विश्लेषण',
    weakDay: 'धीमा दिन',
    noneDetected: 'कोई नहीं मिला',
    atAGlance: 'एक नज़र में',
    yourShopInSimpleBlocks: 'आपकी दुकान, सरल ब्लॉक में',
    numbersThatMatter: 'ज़रूरी आंकड़े, बिना किसी उलझन के।',
    revenueTrend: '8-हफ़्ते का बिक्री रुझान',
    transactions: 'कुल लेन-देन',
    bestDay: 'सबसे अच्छा दिन',
    worstDay: 'सबसे धीमा दिन',
    pendingActions: 'लंबित सुझाव',
    review: 'समीक्षा करें →',
    
    // Dynamic Finance & ML
    userLedger: 'व्यक्तिगत वित्तीय हब व ML इंजन',
    currentBalance: 'वॉलेट व खाता शेष',
    monthlyIncome: 'मासिक आय',
    monthlyExpenses: 'मासिक खर्च',
    predictedSpending: 'अनुमानित 30-दिवसीय खर्च (ML)',
    savingsRate: 'बचत दर',
    spendingByCategory: 'श्रेणी अनुसार खर्च विवरण',
    recentTransactions: 'हालिया लेन-देन',
    addTransaction: '+ नया लेन-देन जोड़ें',
    anomalyAlert: 'असामान्य लेन-देन चेतावनी',
    aiInsights: 'व्यक्तिगत वित्तीय सुझाव',
    modelConfidence: 'ML मॉडल सटीकता',
    
    // General
    syntheticNotice: '📊 डेमो / सिंथेटिक डेटा — प्रदर्शन के लिए सत्यापित गणनाएं।',
    loading: 'लोड हो रहा है...',
    save: 'सुरक्षित करें',
    cancel: 'रद्द करें',
    amount: 'राशि',
    description: 'विवरण',
    category: 'श्रेणी',
    type: 'प्रकार',
    date: 'तारीख',
    allRightsReserved: 'Paytm बिल्ड फॉर इंडिया हैकथॉन',
  }
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('paytm_lang') || 'en')

  const toggleLang = () => {
    const next = lang === 'en' ? 'hi' : 'en'
    setLang(next)
    localStorage.setItem('paytm_lang', next)
  }

  const t = (key) => translations[lang]?.[key] || translations.en[key] || key

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
