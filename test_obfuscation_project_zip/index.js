/**
 * CodeVault Test Application
 * This demonstrates various JavaScript features to test the license protection wrapper.
 */

const utils = require('./utils');

// ========================================
// Configuration
// ========================================
const APP_VERSION = '2.0.0';
const SECRET_API_KEY = process.env.SECRET_API_KEY || 'YOUR_API_KEY_HERE';
const DATABASE_URL = process.env.DATABASE_URL || 'YOUR_DATABASE_URL_HERE';

// ========================================
// Test Functions
// ========================================

function printHeader() {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║           🔒 CodeVault Test Application v' + APP_VERSION + '            ║');
    console.log('║               License Protection Demo                       ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    console.log('');
}

function testSecretStorage() {
    console.log('📦 TEST 1: Secret Storage');
    console.log('   ├─ API Key (first 10 chars): ' + SECRET_API_KEY.substring(0, 10) + '...');
    console.log('   ├─ Database URL loaded: ' + (DATABASE_URL.length > 0 ? '✅ Yes' : '❌ No'));
    console.log('   └─ Status: ✅ PASSED');
    console.log('');
}

function testMathOperations() {
    console.log('🧮 TEST 2: Math Operations (using utils.js)');
    const a = 42, b = 17;
    const sum = utils.add(a, b);
    const expected = 59;
    const passed = sum === expected;
    console.log('   ├─ add(' + a + ', ' + b + ') = ' + sum);
    console.log('   ├─ Expected: ' + expected);
    console.log('   └─ Status: ' + (passed ? '✅ PASSED' : '❌ FAILED'));
    console.log('');
    return passed;
}

function testStringGeneration() {
    console.log('🔤 TEST 3: Random String Generation');
    const id1 = utils.generateId();
    const id2 = utils.generateId();
    const passed = id1 !== id2 && id1.length > 0;
    console.log('   ├─ Generated ID 1: ' + id1);
    console.log('   ├─ Generated ID 2: ' + id2);
    console.log('   ├─ IDs are unique: ' + (id1 !== id2 ? '✅ Yes' : '❌ No'));
    console.log('   └─ Status: ' + (passed ? '✅ PASSED' : '❌ FAILED'));
    console.log('');
    return passed;
}

function testAsyncOperation() {
    console.log('⏱️  TEST 4: Async Simulation');
    console.log('   ├─ Simulating 1 second delay...');

    return new Promise((resolve) => {
        setTimeout(() => {
            console.log('   ├─ Delay completed!');
            console.log('   └─ Status: ✅ PASSED');
            console.log('');
            resolve(true);
        }, 1000);
    });
}

function testEnvironmentInfo() {
    console.log('💻 TEST 5: Environment Information');
    console.log('   ├─ Node Version: ' + process.version);
    console.log('   ├─ Platform: ' + process.platform);
    console.log('   ├─ Architecture: ' + process.arch);
    console.log('   ├─ Process ID: ' + process.pid);
    console.log('   ├─ Working Directory: ' + process.cwd().substring(0, 40) + '...');
    console.log('   └─ Status: ✅ PASSED');
    console.log('');
}

function printSummary(results) {
    const passed = results.filter(r => r).length;
    const total = results.length;
    const allPassed = passed === total;

    console.log('═'.repeat(60));
    console.log('');
    console.log('📊 TEST SUMMARY');
    console.log('   ├─ Tests Passed: ' + passed + '/' + total);
    console.log('   ├─ Success Rate: ' + Math.round((passed / total) * 100) + '%');
    console.log('   └─ Overall: ' + (allPassed ? '✅ ALL TESTS PASSED!' : '❌ SOME TESTS FAILED'));
    console.log('');
    console.log('═'.repeat(60));
    console.log('');
    console.log('🎉 If you can see this, the CodeVault license wrapper is working!');
    console.log('   Your protected application runs successfully after validation.');
    console.log('');
}

// ========================================
// Main Entry Point
// ========================================

async function main() {
    printHeader();

    const results = [];

    // Run all tests
    testSecretStorage();
    results.push(true);

    results.push(testMathOperations());
    results.push(testStringGeneration());

    // Async test
    const asyncResult = await testAsyncOperation();
    results.push(asyncResult);

    testEnvironmentInfo();
    results.push(true);

    // Print summary
    printSummary(results);
}

// Run the application
main();
