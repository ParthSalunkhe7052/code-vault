const crypto = require('crypto');

function add(a, b) {
    return a + b;
}

function generateId() {
    // Use cryptographically secure random UUID generation
    return crypto.randomUUID();
}

module.exports = {
    add,
    generateId
};
