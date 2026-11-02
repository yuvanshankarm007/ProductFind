"""
Internationalization (i18n) Engine for Multilingual Multi-Agent Swarm.
Supports English, Hindi, Spanish, German, French, and Japanese.
Translates agent negotiation events, strategy summaries, and UI payloads.
"""

from typing import Dict, Any

SUPPORTED_LANGUAGES = {
    "en": "English 🇺🇸",
    "hi": "हिंदी (Hindi) 🇮🇳",
    "es": "Español (Spanish) 🇪🇸",
    "de": "Deutsch (German) 🇩🇪",
    "fr": "Français (French) 🇫🇷",
    "ja": "日本語 (Japanese) 🇯🇵"
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "dispatch_scouts": "Deploying scout agents for query: '{query}' across domestic and global retailers.",
        "scouted_listing": "Scouted {merchant} listing: {title} at {price} (Condition: {condition}, Origin: {country})",
        "deep_scrape_query": "Deep-scraping fine print terms for listing [{id}]: inspecting field '{field}'...",
        "verified_fine_print": "Deep-scrape complete for [{id}]: Verified deductible = {deductible}, Accidental drops/spills confirmed.",
        "trust_rating": "Merchant [{merchant}] Trust Rating: {score}/100 ({tier}). Restocking fee: {fee}%, COD: {cod}, Open Box: {open_box}.",
        "paypal_synergy": "PayPal Protection Shield configured for [{id}]: {headline}. Pay in 4 = {pay_in_4}/biweekly.",
        "cross_border_detected": "Cross-Border Merchant detected ({origin} → {dest}). Live FX: 1 {orig_curr} = {rate} {dest_curr}. Estimated Customs Duty: {duty}%. Credit Card 3.5% fee vs PayPal Native Shield.",
        "price_prediction_log": "Price Prediction Agent: Analyzed 90-day history. Prediction: {trend} (Delta: {delta}%). Verdict: {verdict} (Confidence: {confidence}%).",
        "optimal_value": "Optimal Value Champion",
        "max_protection": "Maximum ADP Protection",
        "budget_sticker": "Budget (Requires Caution)",
        "cod_available": "Cash on Delivery Available",
        "cod_unavailable": "Prepaid Online Only (No COD)",
        "open_box_available": "Open Box Delivery (Inspect Before OTP)",
        "open_box_unavailable": "Standard Sealed Courier Delivery",
        "exchange_offer": "Exchange / Trade-in Available (Up to {amount} discount)",
        "preferred_payment_match": "Matches Preferred Payment: {payment}",
        "paypal_shield_active": "PayPal 180-Day Buyer Protection Active"
    },
    "hi": {
        "dispatch_scouts": "खोज एजेंट तैनात किए जा रहे हैं: '{query}' के लिए घरेलू और वैश्विक खुदरा विक्रेताओं में खोज जारी है।",
        "scouted_listing": "{merchant} से उत्पाद मिला: {title} मूल्य {price} (स्थिति: {condition}, मूल देश: {country})",
        "deep_scrape_query": "लिस्टिंग [{id}] के लिए बारीक शर्तों की गहरी जांच: फील्ड '{field}' का विश्लेषण...",
        "verified_fine_print": "[{id}] की गहन जांच पूर्ण: सत्यापित कटौती = {deductible}, आकस्मिक क्षति कवरेज की पुष्टि।",
        "trust_rating": "विक्रेता [{merchant}] ट्रस्ट स्कोर: {score}/100 ({tier})। रीस्टॉकिंग शुल्क: {fee}%, कैश ऑन डिलीवरी: {cod}, ओपन बॉक्स: {open_box}।",
        "paypal_synergy": "[{id}] के लिए पेपाल सुरक्षा शील्ड सक्रिय: {headline}। पे इन 4 = {pay_in_4}/पाक्षिक।",
        "cross_border_detected": "अंतरराष्ट्रीय विक्रेता पाया गया ({origin} → {dest})। लाइव विनिमय दर: 1 {orig_curr} = {rate} {dest_curr}। अनुमानित सीमा शुल्क: {duty}%। पेपाल मुद्रा रूपांतरण की सिफारिश।",
        "price_prediction_log": "मूल्य भविष्यवाणी एजेंट: 90 दिनों के इतिहास का विश्लेषण। पूर्वानुमान: {trend} ({delta}%)। निर्णय: {verdict} (सटीकता: {confidence}%)।",
        "optimal_value": "सर्वश्रेष्ठ समग्र मूल्य विजेता",
        "max_protection": "अधिकतम वारंटी और सुरक्षा",
        "budget_sticker": "कम बजट (सावधानी आवश्यक)",
        "cod_available": "कैश ऑन डिलीवरी (COD) उपलब्ध है",
        "cod_unavailable": "केवल ऑनलाइन पूर्व-भुगतान (COD नहीं)",
        "open_box_available": "ओपन बॉक्स डिलीवरी (OTP से पहले खोलकर जांचें)",
        "open_box_unavailable": "सामान्य सीलबंद पार्सल डिलीवरी",
        "exchange_offer": "पुराना उत्पाद बदलें (एक्सचेंज पर {amount} तक छूट)",
        "preferred_payment_match": "आपकी पसंदीदा भुगतान विधि समर्थित: {payment}",
        "paypal_shield_active": "पेपाल 180-दिवसीय खरीदार सुरक्षा सक्रिय"
    },
    "es": {
        "dispatch_scouts": "Desplegando agentes de búsqueda para la consulta: '{query}' en comercios locales y globales.",
        "scouted_listing": "Oferta encontrada en {merchant}: {title} a {price} (Estado: {condition}, Origen: {country})",
        "deep_scrape_query": "Extracción profunda de términos de letra pequeña para [{id}]: campo '{field}'...",
        "verified_fine_print": "Análisis profundo completado para [{id}]: Deducible verificado = {deductible}, Cobertura contra caídas/derrames confirmada.",
        "trust_rating": "Reputación del comercio [{merchant}]: {score}/100 ({tier}). Tarifa de reabastecimiento: {fee}%, Pago contra entrega: {cod}, Entrega caja abierta: {open_box}.",
        "paypal_synergy": "Escudo de Protección PayPal configurado para [{id}]: {headline}. Paga en 4 = {pay_in_4}/quincenal.",
        "cross_border_detected": "Comercio internacional detectado ({origin} → {dest}). Tipo de cambio en vivo: 1 {orig_curr} = {rate} {dest_curr}. Arancel aduanero estimado: {duty}%.",
        "price_prediction_log": "Agente de predicción de precios: Historial de 90 días analizado. Pronóstico: {trend} ({delta}%). Veredicto: {verdict} (Confianza: {confidence}%).",
        "optimal_value": "Campeón de Valor Óptimo",
        "max_protection": "Máxima Protección contra Daños",
        "budget_sticker": "Económico (Requiere Precaución)",
        "cod_available": "Pago Contra Entrega (COD) Disponible",
        "cod_unavailable": "Solo Prepago en Línea (Sin COD)",
        "open_box_available": "Entrega en Caja Abierta (Inspección Previa con OTP)",
        "open_box_unavailable": "Entrega Estándar Sellada",
        "exchange_offer": "Oferta de Canje / Reemplazo (Hasta {amount} de descuento)",
        "preferred_payment_match": "Coincide con Pago Preferido: {payment}",
        "paypal_shield_active": "Protección al Comprador PayPal de 180 Días Activa"
    },
    "de": {
        "dispatch_scouts": "Scout-Agenten werden für '{query}' bei in- und ausländischen Händlern eingesetzt.",
        "scouted_listing": "Gefundenes Angebot bei {merchant}: {title} für {price} (Zustand: {condition}, Herkunft: {country})",
        "deep_scrape_query": "Tiefenanalyse des Kleingedruckten für [{id}]: Feld '{field}' wird geprüft...",
        "verified_fine_print": "Tiefenanalyse für [{id}] abgeschlossen: Selbstbeteiligung = {deductible}, Unfallschutz bestätigt.",
        "trust_rating": "Händler-Vertrauensbewertung [{merchant}]: {score}/100 ({tier}). Rücknahmegebühr: {fee}%, Nachnahme: {cod}, Open-Box-Lieferung: {open_box}.",
        "paypal_synergy": "PayPal-Käuferschutzschild für [{id}] konfiguriert: {headline}. Pay in 4 = {pay_in_4}/zweiwöchentlich.",
        "cross_border_detected": "Grenzüberschreitender Händler erkannt ({origin} → {dest}). Live-Wechselkurs: 1 {orig_curr} = {rate} {dest_curr}. Geschätzter Zoll: {duty}%.",
        "price_prediction_log": "Preisprognose-Agent: 90-Tage-Historie analysiert. Prognose: {trend} ({delta}%). Empfehlung: {verdict} (Konfidenz: {confidence}%).",
        "optimal_value": "Optimaler Preis-Leistungs-Sieger",
        "max_protection": "Maximaler Geräteschutz (ADP)",
        "budget_sticker": "Günstigstes Angebot (Vorsicht geboten)",
        "cod_available": "Zahlung per Nachnahme verfügbar",
        "cod_unavailable": "Nur Online-Vorkasse (Keine Nachnahme)",
        "open_box_available": "Open-Box-Lieferung (Prüfung vor Übergabe-OTP)",
        "open_box_unavailable": "Standard-Versandversiegelt",
        "exchange_offer": "Eintausch- / Rabattaktion (Bis zu {amount} Rabatt)",
        "preferred_payment_match": "Entspricht bevorzugter Zahlungsart: {payment}",
        "paypal_shield_active": "180 Tage PayPal-Käuferschutz Aktiv"
    },
    "fr": {
        "dispatch_scouts": "Déploiement des agents de recherche pour la requête: '{query}' auprès des commerçants nationaux et internationaux.",
        "scouted_listing": "Offre trouvée chez {merchant}: {title} à {price} (État: {condition}, Origine: {country})",
        "deep_scrape_query": "Extraction approfondie des conditions générales pour [{id}]: examen du champ '{field}'...",
        "verified_fine_print": "Analyse approfondie terminée pour [{id}]: Franchise vérifiée = {deductible}, Couverture casse/liquide confirmée.",
        "trust_rating": "Score de confiance du vendeur [{merchant}]: {score}/100 ({tier}). Frais de réapprovisionnement: {fee}%, Paiement à la livraison: {cod}, Livraison boîte ouverte: {open_box}.",
        "paypal_synergy": "Bouclier de Protection PayPal configuré pour [{id}]: {headline}. Paiement en 4x = {pay_in_4}/toutes les deux semaines.",
        "cross_border_detected": "Commerçant international détecté ({origin} → {dest}). Taux de change en direct: 1 {orig_curr} = {rate} {dest_curr}. Droits de douane estimés: {duty}%.",
        "price_prediction_log": "Agent de prédiction de prix: Historique sur 90 jours analysé. Tendance: {trend} ({delta}%). Verdict: {verdict} (Confiance: {confidence}%).",
        "optimal_value": "Champion du Meilleur Rapport Qualité/Prix",
        "max_protection": "Protection Maximale contre les Dommages",
        "budget_sticker": "Prix le Plus Bas (Prudence Requise)",
        "cod_available": "Paiement à la livraison disponible",
        "cod_unavailable": "Paiement en ligne anticipé uniquement",
        "open_box_available": "Livraison en boîte ouverte (Vérification avant OTP)",
        "open_box_unavailable": "Livraison sous colis scellé standard",
        "exchange_offer": "Offre de reprise / échange (Jusqu'à {amount} de réduction)",
        "preferred_payment_match": "Compatible avec le moyen de paiement préféré: {payment}",
        "paypal_shield_active": "Protection des Achats PayPal 180 Jours Active"
    },
    "ja": {
        "dispatch_scouts": "クエリ '{query}' のために国内および海外の販売店に対して偵察エージェントを展開中...",
        "scouted_listing": "{merchant} で商品を発見: {title} 価格 {price} (状態: {condition}, 発送元: {country})",
        "deep_scrape_query": "リスティング [{id}] の利用規約詳細を分析中: フィールド '{field}' を調査...",
        "verified_fine_print": "[{id}] の詳細調査完了: 自己負担金 = {deductible}, 落下・水濡れ保証を確認。",
        "trust_rating": "販売者 [{merchant}] 信頼度スコア: {score}/100 ({tier})。返品手数料: {fee}%, 代金引換: {cod}, 開封確認配送: {open_box}。",
        "paypal_synergy": "[{id}] にPayPalバイヤープロテクションシールドを設定: {headline}。4回分割払い = {pay_in_4}/隔週。",
        "cross_border_detected": "海外加盟店を検出 ({origin} → {dest})。リアルタイム為替レート: 1 {orig_curr} = {rate} {dest_curr}。推定関税: {duty}%。PayPal通貨換算を推奨。",
        "price_prediction_log": "価格予測エージェント: 90日間の価格履歴を分析。予測: {trend} ({delta}%)。判定: {verdict} (信頼度: {confidence}%)。",
        "optimal_value": "最適総合バリュー優秀賞",
        "max_protection": "最大保証・物損プロテクション",
        "budget_sticker": "最安値（注意が必要な並行輸入/規約）",
        "cod_available": "代金引換 (COD) 利用可能",
        "cod_unavailable": "事前オンライン決済のみ（代引き不可）",
        "open_box_available": "開封確認配送対応（受け取りOTP入力前に中身を確認可能）",
        "open_box_unavailable": "通常密閉配送",
        "exchange_offer": "下取り・買替割引あり（最大 {amount} 引）",
        "preferred_payment_match": "ご希望のお支払い方法に対応: {payment}",
        "paypal_shield_active": "PayPal 180日間買い手保護制度適用"
    }
}

def translate(key: str, lang: str = "en", **kwargs) -> str:
    lang = lang.lower() if lang else "en"
    if lang not in TRANSLATIONS:
        lang = "en"
    
    template = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
