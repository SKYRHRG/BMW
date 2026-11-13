// razorpay_upi.js
// FINAL UNIVERSAL VERSION - 8.0
// This script now handles the specific multi-step mobile workflow provided by the user.

if (window.location.hostname === 'api.razorpay.com') {

    console.log("Correct Razorpay iframe (api.razorpay.com) detected. Automation script will run.");
    let user_data = {};

    function simulateAdvancedClick(element, elementName) {
        if (element) {
            if (element.offsetParent === null || element.disabled) {
                console.warn(`Attempted to click ${elementName}, but it's not visible or is disabled.`, element);
                return false;
            }
            console.log(`Performing advanced click on ${elementName}:`, element);
            element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            return true;
        } else {
            console.warn(`${elementName} not found or is not clickable.`, element);
            return false;
        }
    }

    function waitForElement(findLogic, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const element = findLogic();
            if (element) return resolve(element);
            const observer = new MutationObserver(() => {
                const el = findLogic();
                if (el) {
                    clearTimeout(timer);
                    observer.disconnect();
                    resolve(el);
                }
            });
            const timer = setTimeout(() => {
                observer.disconnect();
                reject(new Error(`waitForElement timed out for selector.`));
            }, timeout);
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }

    // ==========================================================
    //  LOGIC FOR DESKTOP VIEW (width > 512px) - NO CHANGES
    // ==========================================================
    async function runDesktopLogic() {
        try {
            const targetLabel = await waitForElement(() => {
                const upiSpan = document.querySelector('span[data-testid="BHIM/UPI"]');
                return upiSpan ? upiSpan.closest('label') : null;
            });
            console.log("Desktop UPI Label found! Clicking it now.");
            if (simulateAdvancedClick(targetLabel, 'BHIM/UPI Label')) {
                await fillVpaAndProceed('button[data-testid="vpa-submit"]');
            }
        } catch (error) {
            console.error("Desktop Logic Error:", error.message);
        }
    }

    // ==========================================================
    //  LOGIC FOR MOBILE VIEW (width <= 512px) - NEW & UPDATED
    // ==========================================================
    async function runMobileLogic() {
        console.log('Mobile logic initiated.');
        try {
            // Step 1 (Mobile): Click the main UPI category button
            const categoryButton = await waitForElement(() => document.querySelector('div[data-value="upi"][data-index="-1"]'));
            console.log("Mobile UPI Category button found. Clicking it...");
            simulateAdvancedClick(categoryButton, 'Mobile UPI Category Button');

            // Step 2 (Mobile): Click the first "Continue" button to show the input field
            const firstContinueBtn = await waitForElement(() => document.querySelector('button[data-testid="bottom-cta-button"][preventsubmit="true"]'));
            console.log("First 'Continue' button found. Clicking to reveal VPA input...");
            simulateAdvancedClick(firstContinueBtn, 'First Continue Button');
            
            // Step 3 (Mobile): Fill the VPA and click the second "Continue" (Verify) button
            await fillVpaAndProceed('button[data-testid="bottom-cta-button"][validateform="true"]');

        } catch (error) {
            console.error("Mobile Logic Error:", error.message);
            alert("Automation failed on mobile view.");
        }
    }

    // ==========================================================
    //  SHARED LOGIC TO FILL VPA AND COMPLETE PAYMENT
    // ==========================================================
    async function fillVpaAndProceed(verifyButtonSelector) {
        try {
            console.log('Waiting for VPA input field...');
            const vpaInputElement = await waitForElement(() => document.querySelector('input[name="vpa"]'));
            console.log('VPA input field appeared. Filling details...');
            
            if (user_data?.vpa?.vpa) {
                const vpaValue = user_data.vpa.vpa;
                vpaInputElement.focus();
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(vpaInputElement, vpaValue);
                vpaInputElement.dispatchEvent(new Event('input', { bubbles: true }));
                vpaInputElement.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('UPI ID entered:', vpaValue);

                await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms after input

                console.log('Waiting for the Verify button...');
                const verifyButton = await waitForElement(() => document.querySelector(verifyButtonSelector));
                simulateAdvancedClick(verifyButton, 'Verify Button');

                console.log("Waiting for the final 'Continue & Pay' modal/button...");
                const finalPayButton = await waitForElement(() => document.querySelector('button[data-testid="fee-bearer-cta"]'));
                console.log("Final 'Continue & Pay' button found. Clicking it.");
                simulateAdvancedClick(finalPayButton, 'Continue & Pay Button');

            } else {
                console.warn("VPA not found in user data.");
            }
        } catch (error) {
            console.error("Error in fillVpaAndProceed:", error.message);
        }
    }

    // ==========================================================
    //  MAIN EXECUTION BLOCK
    // ==========================================================
    function main() {
        console.log("Checking screen width to determine logic path...");
        if (window.innerWidth <= 512) {
            console.log("Mobile view detected.");
            runMobileLogic();
        } else {
            console.log("Desktop view detected.");
            runDesktopLogic();
        }
    }

    chrome.storage.local.get(null, (result) => {
        user_data = result;
        if (user_data?.other_preferences?.paymentmethod === "RAZORPAYUPI") {
            console.log("Razorpay UPI payment method selected. Initializing...");
            main();
        } else {
            console.log('Not a Razorpay UPI payment method. Script will not run.');
        }
    });
}