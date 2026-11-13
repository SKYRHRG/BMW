// payu_upi.js
// This script will run on the PayU payment gateway page.

// Global variable to store user data loaded from chrome.storage.
let user_data = {};

/**
 * Simulates a click on an element, ensuring it's visible and interactable.
 * @param {HTMLElement} element The element to click.
 * @param {string} elementName A descriptive name for logging.
 */
function simulateClick(element, elementName) {
    if (element && typeof element.click === 'function') {
        // Basic visibility check (can be enhanced)
        if (element.offsetParent === null || element.disabled) {
            console.warn(`Attempted to click ${elementName}, but it's not visible or is disabled.`, element);
            return false;
        }
        console.log(`Clicking ${elementName}:`, element);
        element.click();
        return true;
    } else {
        console.warn(`${elementName} not found or is not clickable.`, element);
        return false;
    }
}


/**
 * Fills the VPA (UPI ID) on the PayU page and clicks the proceed/pay button.
 */
function fillPayUVPA() {
    console.log('fillPayUVPA function initiated for PayU UPI payment.');

    // Step 1: Click the UPI option/card
    // Find the <p> element with class "list-item-title" and text "Pay with UPI ID / Mobile number"
    // Then click its parent <li> element or the <p> itself if it's the clickable target.

    var upiOptionCheckInterval = setInterval(() => {
        const upiTitleElements = Array.from(document.querySelectorAll('p.list-item-title'));
        const targetUpiTitle = upiTitleElements.find(p => p.textContent.trim() === "Pay with UPI ID / Mobile number");
        
        let upiCardToClick = null;
        if (targetUpiTitle) {
            // Try to find the parent <li> with class 'flex-col' as described by user
            let parentLi = targetUpiTitle.closest('li.flex-col');
            if (parentLi) {
                upiCardToClick = parentLi;
                console.log('UPI card (li.flex-col containing "Pay with UPI ID / Mobile number") found:', upiCardToClick);
            } else {
                // Fallback to clicking the title itself if parent structure isn't exactly as expected
                upiCardToClick = targetUpiTitle;
                console.warn('Parent li.flex-col not found for UPI title, will try to click the title <p> element directly.');
            }
        }

        if (upiCardToClick) {
            clearInterval(upiOptionCheckInterval);
            if (!simulateClick(upiCardToClick, 'UPI Option Card/Title')) {
                alert('Could not click the UPI option. Please select it manually.');
                return;
            }

            // Wait for the UPI input field to become available after clicking the UPI option
            setTimeout(() => {
                // Step 2: Fill the UPI ID input field
                const vpaInputElement = document.querySelector('#upi2Id'); // User-provided ID

                if (vpaInputElement) {
                    console.log('PayU VPA input field (#upi2Id) found:', vpaInputElement);

                    if (user_data && user_data.vpa && user_data.vpa.vpa) {
                        const vpaValue = user_data.vpa.vpa;
                        console.log('Populating PayU VPA input field with:', vpaValue);

                        vpaInputElement.focus();
                        
                        // Clear existing value and dispatch input event
                        vpaInputElement.value = '';
                        vpaInputElement.dispatchEvent(new Event('input', { bubbles: true }));

                        // Use native value setter for frameworks like React/Angular
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        if (nativeInputValueSetter) {
                            nativeInputValueSetter.call(vpaInputElement, vpaValue);
                        } else {
                            vpaInputElement.value = vpaValue; // Fallback
                        }
                        
                        // Dispatch events to ensure the page recognizes the change
                        vpaInputElement.dispatchEvent(new Event('input', { bubbles: true }));
                        vpaInputElement.dispatchEvent(new Event('change', { bubbles: true }));
                        vpaInputElement.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true })); // Simulate keyup

                        console.log('UPI ID entered into #upi2Id with all events. Current value:', vpaInputElement.value);

                        // Wait a bit before clicking Verify
                        setTimeout(() => {
                            // Step 3: Click the Verify button
                            const verifyButtonElement = document.querySelector('#upi-verify-enabled'); // User-provided ID

                            if (!simulateClick(verifyButtonElement, 'Verify UPI Button (#upi-verify-enabled)')) {
                                // alert('Could not click the Verify UPI button. Please click it manually.');
                                // Don't necessarily stop if verify button isn't immediately clickable, 
                                // sometimes it enables after a delay or the proceed button becomes active.
                                console.warn('Verify button was not clicked or found. Checking for PROCEED button anyway.');
                            }

                            // Wait a bit before clicking Proceed
                            setTimeout(() => {
                                // Step 4: Click the PROCEED button (span)
                                const proceedSpanElements = Array.from(document.querySelectorAll('span'));
                                const proceedButtonElement = proceedSpanElements.find(span => span.textContent.trim().toUpperCase() === 'PROCEED');

                                if (!simulateClick(proceedButtonElement, 'PROCEED Button (span)')) {
                                    alert('Could not click the PROCEED button. Please click it manually.');
                                }
                            }, 800); // Adjust delay after Verify click as needed

                        }, 500); // Adjust delay after VPA input as needed

                    } else {
                        console.warn('VPA (UPI ID) not found in user_data for PayU flow.');
                        alert('Your UPI ID is not saved. Please save it in the extension and try again.');
                    }
                } else {
                    console.warn('PayU VPA input field (#upi2Id) NOT found after clicking UPI option.');
                    alert('Could not find the UPI ID input field. Please check the PayU page structure.');
                }
            }, 700); // Adjust delay after clicking UPI option

        } else {
            console.log('PayU UPI option/card not yet available. Retrying...');
        }
    }, 500); // Check for the UPI option every 500 milliseconds
}

// Main execution block: Load user data and trigger the VPA filling logic.
chrome.storage.local.get(null, (result) => {
    user_data = result;
    console.log('User data loaded on PayU page:', user_data);

    // Check if the current payment method is indeed for PayU UPI ID.
    if (user_data && user_data.other_preferences && user_data.other_preferences.paymentmethod === "PAYUUPIID") {
        console.log('PayU UPI ID payment method selected. Initializing PayU VPA fill.');

        // Wait for the document to be fully loaded before trying to interact with elements.
        if (document.readyState !== 'loading') {
            fillPayUVPA();
        } else {
            document.addEventListener('DOMContentLoaded', function () {
                console.log('DOMContentLoaded event fired on PayU page. Calling fillPayUVPA.');
                fillPayUVPA();
            });
        }
    } else {
        console.log('Not a PayU UPI ID payment method, or payment method not found. PayU script will not run automation.');
    }
});
