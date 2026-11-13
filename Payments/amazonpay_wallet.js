// amazonpay_wallet.js

// सहायक फ़ंक्शन: किसी एलिमेंट के दिखने और इंटरैक्ट करने योग्य होने की प्रतीक्षा करता है
function waitForElement(selector) {
    return new Promise(resolve => {
        // यदि एलिमेंट पहले से ही मौजूद है, तो तुरंत लौटें
        const element = document.querySelector(selector);
        if (element) {
            return resolve(element);
        }

        // यदि नहीं, तो एक पर्यवेक्षक (observer) सेट करें
        const observer = new MutationObserver(mutations => {
            const element = document.querySelector(selector);
            if (element) {
                resolve(element);
                observer.disconnect();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

// मुख्य तर्क
async function automateAmazonPay() {
    console.log("Amazon Pay Wallet स्क्रिप्ट सक्रिय है।");

    // आपके द्वारा प्रदान किया गया सटीक बटन चयनकर्ता
    const payButtonSelector = 'input[type="submit"][name="ppw-widgetEvent:SetPaymentPlanSelectContinueEvent"]';

    try {
        // बटन के लोड होने की प्रतीक्षा करें
        const payButton = await waitForElement(payButtonSelector);
        console.log("Amazon Pay 'Continue' बटन मिला:", payButton);
        
        // जांचें कि उपयोगकर्ता ने मैन्युअल भुगतान तो नहीं चुना है
        chrome.storage.local.get('other_preferences', (data) => {
            // यदि paymentManual चेक नहीं है, तो ही स्वचालित रूप से क्लिक करें
            if (data.other_preferences && !data.other_preferences.paymentManual) { //
                setTimeout(() => {
                    payButton.click();
                    console.log("Amazon Pay 'Continue' बटन पर क्लिक किया गया।");
                }, 1500); // 1.5 सेकंड का विलंब ताकि पेज पूरी तरह से लोड हो जाए
            } else {
                console.log("मैन्युअल भुगतान मोड सक्रिय है। कृपया स्वयं भुगतान पूरा करें।");
            }
        });

    } catch (error) {
        console.error("Amazon Pay 'Continue' बटन नहीं मिला या कोई त्रुटि हुई:", error);
    }
}

// स्क्रिप्ट शुरू करें
automateAmazonPay();