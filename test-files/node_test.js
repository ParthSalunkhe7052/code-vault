/**
 * CodeVault Cloud Build Test - Node.js
 * A simple test file to verify cloud compilation works correctly.
 */

const os = require('os');
const fs = require('fs');
const path = require('path');

function runTests() {
    console.log('='.repeat(50));
    console.log('CodeVault Cloud Build - Node.js Test Suite');
    console.log('='.repeat(50));
    console.log();
    
    let testsPassed = 0;
    let testsFailed = 0;
    
    // Test 1: Node Version
    console.log('Test 1: Node.js Version Check');
    const nodeVersion = process.version;
    const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
    console.log(`  Node version: ${nodeVersion}`);
    if (majorVersion >= 14) {
        console.log('  Result: PASS (Node 14+)');
        testsPassed++;
    } else {
        console.log('  Result: FAIL (Node too old)');
        testsFailed++;
    }
    console.log();
    
    // Test 2: Platform Detection
    console.log('Test 2: Platform Detection');
    console.log(`  Platform: ${process.platform}`);
    console.log(`  Architecture: ${process.arch}`);
    console.log(`  OS Type: ${os.type()}`);
    console.log('  Result: PASS');
    testsPassed++;
    console.log();
    
    // Test 3: Working Directory
    console.log('Test 3: Working Directory');
    console.log(`  Current directory: ${process.cwd()}`);
    console.log('  Result: PASS');
    testsPassed++;
    console.log();
    
    // Test 4: Basic Math Operations
    console.log('Test 4: Basic Math Operations');
    const result = (10 + 20) * 2 - 5;
    const expected = 55;
    if (result === expected) {
        console.log(`  Calculation: (10 + 20) * 2 - 5 = ${result}`);
        console.log('  Result: PASS');
        testsPassed++;
    } else {
        console.log(`  Expected ${expected}, got ${result}`);
        console.log('  Result: FAIL');
        testsFailed++;
    }
    console.log();
    
    // Test 5: String Operations
    console.log('Test 5: String Operations');
    const testStr = 'Hello, CodeVault!';
    const upper = testStr.toUpperCase();
    const length = testStr.length;
    if (upper === 'HELLO, CODEVAULT!' && length === 17) {
        console.log(`  Original: '${testStr}'`);
        console.log(`  Upper: '${upper}'`);
        console.log(`  Length: ${length}`);
        console.log('  Result: PASS');
        testsPassed++;
    } else {
        console.log('  Result: FAIL');
        testsFailed++;
    }
    console.log();
    
    // Test 6: Array Operations
    console.log('Test 6: Array Operations');
    const numbers = [1, 2, 3, 4, 5];
    const doubled = numbers.map(x => x * 2);
    if (JSON.stringify(doubled) === JSON.stringify([2, 4, 6, 8, 10])) {
        console.log(`  Input: [${numbers}]`);
        console.log(`  Doubled: [${doubled}]`);
        console.log('  Result: PASS');
        testsPassed++;
    } else {
        console.log('  Result: FAIL');
        testsFailed++;
    }
    console.log();
    
    // Test 7: Object Operations
    console.log('Test 7: Object Operations');
    const config = {
        appName: 'CodeVault',
        version: '1.0.0',
        debug: false
    };
    if (config.appName === 'CodeVault' && 'version' in config) {
        console.log(`  Config: ${JSON.stringify(config)}`);
        console.log('  Result: PASS');
        testsPassed++;
    } else {
        console.log('  Result: FAIL');
        testsFailed++;
    }
    console.log();
    
    // Test 8: File Operations
    console.log('Test 8: File Operations');
    try {
        const testFile = path.join(process.cwd(), 'test_output.txt');
        fs.writeFileSync(testFile, 'CodeVault test file\n');
        const content = fs.readFileSync(testFile, 'utf8');
        fs.unlinkSync(testFile);
        if (content === 'CodeVault test file\n') {
            console.log('  Write/Read/Delete: SUCCESS');
            console.log('  Result: PASS');
            testsPassed++;
        } else {
            console.log('  Content mismatch');
            console.log('  Result: FAIL');
            testsFailed++;
        }
    } catch (e) {
        console.log(`  Error: ${e.message}`);
        console.log('  Result: FAIL');
        testsFailed++;
    }
    console.log();
    
    // Test 9: Async Operations
    console.log('Test 9: Async/Promise Operations');
    const asyncTest = new Promise((resolve) => {
        setTimeout(() => resolve('async works'), 100);
    });
    
    // Synchronous check of Promise existence
    if (asyncTest instanceof Promise) {
        console.log('  Promise created successfully');
        console.log('  Result: PASS');
        testsPassed++;
    } else {
        console.log('  Result: FAIL');
        testsFailed++;
    }
    console.log();
    
    // Test 10: Memory Info
    console.log('Test 10: System Memory');
    const totalMem = Math.round(os.totalmem() / (1024 * 1024 * 1024));
    const freeMem = Math.round(os.freemem() / (1024 * 1024 * 1024));
    console.log(`  Total Memory: ${totalMem} GB`);
    console.log(`  Free Memory: ${freeMem} GB`);
    console.log('  Result: PASS');
    testsPassed++;
    console.log();
    
    // Summary
    console.log('='.repeat(50));
    console.log('TEST SUMMARY');
    console.log('='.repeat(50));
    console.log(`  Tests Passed: ${testsPassed}`);
    console.log(`  Tests Failed: ${testsFailed}`);
    console.log(`  Total Tests: ${testsPassed + testsFailed}`);
    console.log();
    
    if (testsFailed === 0) {
        console.log('  Status: ALL TESTS PASSED!');
    } else {
        console.log(`  Status: ${testsFailed} TEST(S) FAILED`);
    }
    
    console.log('='.repeat(50));
    
    // Keep window open for 5 seconds
    console.log('\nClosing in 5 seconds...');
    setTimeout(() => {
        process.exit(testsFailed === 0 ? 0 : 1);
    }, 5000);
}

// Run tests
runTests();