function add(a, b) {
    return a + b;
}

function generateId() {
    return Math.random().toString(36).substring(7);
}

module.exports = {
    add,
    generateId
};
