// Runs before module loading so import/JSON/worker failures reach the native host.
window.printFinsMessage = message => window.wx.postMessage(JSON.stringify(message));
window.addEventListener('error', event => window.printFinsMessage({ action: 'error', error: event.message || 'Cannot load PrintFins resources.' }));
window.addEventListener('unhandledrejection', event => window.printFinsMessage({ action: 'error', error: String(event.reason) }));
