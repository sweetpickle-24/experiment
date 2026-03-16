#!/bin/bash
# Monitor concentration invariance test
# This script will check progress every 2 minutes and report when complete

LOG_FILE="/Users/vladyslav/Documents/GitHub/experiment/concentration_test_output.log"
RESULT_FILE="/Users/vladyslav/Documents/GitHub/experiment/concentration_invariance_results.json"
STATUS_FILE="/Users/vladyslav/Documents/GitHub/experiment/test_status.txt"

echo "Starting monitoring at $(date)" > "$STATUS_FILE"
echo "Log file: $LOG_FILE" >> "$STATUS_FILE"
echo "" >> "$STATUS_FILE"

for i in {1..30}; do  # Monitor for up to 60 minutes (30 × 2 min)
    sleep 120  # Check every 2 minutes
    
    echo "=== Check $i at $(date +%H:%M:%S) ===" >> "$STATUS_FILE"
    
    # Check if results file exists (test completed successfully)
    if [ -f "$RESULT_FILE" ]; then
        echo "✅ TEST COMPLETED SUCCESSFULLY!" >> "$STATUS_FILE"
        echo "Results saved to: $RESULT_FILE" >> "$STATUS_FILE"
        
        # Extract summary statistics
        if command -v python3 &> /dev/null; then
            python3 << 'PYTHON_EOF' >> "$STATUS_FILE"
import json
try:
    with open('/Users/vladyslav/Documents/GitHub/experiment/concentration_invariance_results.json', 'r') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    binary_corr = summary.get('binary_correlation', {})
    jaccard_sim = summary.get('jaccard_similarity', {})
    validation = summary.get('validation', 'unknown')
    
    print("\n" + "="*60)
    print("CONCENTRATION INVARIANCE RESULTS")
    print("="*60)
    print(f"Binary Correlation: {binary_corr.get('mean', 0):.3f} ± {binary_corr.get('std', 0):.3f}")
    print(f"Jaccard Similarity: {jaccard_sim.get('mean', 0):.3f} ± {jaccard_sim.get('std', 0):.3f}")
    print(f"Validation Status: {validation.upper()}")
    print("="*60)
except Exception as e:
    print(f"Could not parse results: {e}")
PYTHON_EOF
        fi
        
        exit 0
    fi
    
    # Check if process is still running
    if pgrep -f "concentration_invariance_test.py" > /dev/null; then
        echo "  Status: Running..." >> "$STATUS_FILE"
        
        # Check log file size
        if [ -f "$LOG_FILE" ]; then
            LOG_SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo "0")
            echo "  Log size: $LOG_SIZE bytes" >> "$STATUS_FILE"
            
            # Show last few lines if available
            if [ "$LOG_SIZE" -gt 0 ]; then
                echo "  Last output:" >> "$STATUS_FILE"
                tail -5 "$LOG_FILE" >> "$STATUS_FILE" 2>/dev/null || echo "  (log not readable yet)" >> "$STATUS_FILE"
            fi
        fi
    else
        echo "❌ PROCESS NO LONGER RUNNING" >> "$STATUS_FILE"
        
        # Check for errors in log
        if [ -f "$LOG_FILE" ]; then
            echo "  Last 20 lines of log:" >> "$STATUS_FILE"
            tail -20 "$LOG_FILE" >> "$STATUS_FILE" 2>/dev/null
        fi
        
        exit 1
    fi
    
    echo "" >> "$STATUS_FILE"
done

echo "⚠️ TIMEOUT: Test did not complete within 60 minutes" >> "$STATUS_FILE"
exit 2
