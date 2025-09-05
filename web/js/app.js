// web/js/app.js

// Import the core modules of our application.
// We will create these files in the upcoming steps.
import { initState, state } from './state.js';
import { initApi } from './api.js';
import { initUI } from './ui.js';

/**
 * @typedef {import('./state.js').AppState} AppState
 */

/**
 * Main application class.
 * This class orchestrates the different modules of the application.
 * @property {AppState} state - The reactive state object.
 */
class VDMApp {
    constructor() {
        this.state = state;
        this.api = null;
        this.ui = null;
    }

    /**
     * Initializes the entire application.
     * This is the main entry point called when the DOM is ready.
     */
    init() {
        // 1. Initialize the central state management.
        initState();

        // 2. Initialize the UI module, passing it the state object.
        // The UI will be responsible for all DOM manipulations.
        this.ui = initUI(this.state);

        // 3. Initialize the API module, passing it the state and UI.
        // The API module will handle all server communication.
        this.api = initApi(this.state, this.ui);

        // Pass the api module to the UI so that UI elements can trigger API calls.
        this.ui.setApi(this.api);
        
        console.log("VDM Frontend Initialized (Modular).");
    }
}

// --- Application Entry Point ---
// When the DOM is fully loaded, create an instance of our app and initialize it.
document.addEventListener('DOMContentLoaded', () => {
    const app = new VDMApp();
    app.init();
});