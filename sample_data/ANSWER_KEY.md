# Sample Dataset Answer Key & Ground Truth

This document outlines the ground truth planted cases within the generated dataset located in [`sample_data/output/`](file:///Users/rohith/Desktop/Local-Echo-Scan/sample_data/output).

## Experiment Topic
- **Experiment**: Verification of Ohm's Law and Determination of Resistance
- **Shared Template Content**: Every student file contains identical or near-identical text for:
  - **Aim**: To verify Ohm's law and determine resistance via V-I graph.
  - **Apparatus**: Power supply, voltmeter, ammeter, unknown resistor, rheostat, plug key, wires.
  - **Procedure**: Standard 5-step laboratory procedure.
- **Lab Manual**: [`lab_manual.txt`](file:///Users/rohith/Desktop/Local-Echo-Scan/sample_data/output/lab_manual.txt) provides this shared template text so the template removal engine can identify and strip it.

---

## Planted Test Cases

### 1. Direct Copy Pair
- **Students**:
  - `01_Aditya_Sharma.txt`
  - `02_Bhavna_Patel.txt`
- **Relationship**: Direct verbatim copy.
- **Shared Content**:
  - Observations (2.0V to 10.0V readings, average resistance ~49.8 ohms).
  - Calculations (regression slope $\Delta V / \Delta I = 49.69$ ohms, $0.62\%$ error).
  - Conclusion (identical wording confirming linear V-I curve and $49.7$ ohms).
- **Expected Score**: $\ge 0.99$
- **Expected Label**: `"likely copy"`

---

### 2. Reworded Paraphrase Pair
- **Students**:
  - `03_Chirag_Verma.docx` (DOCX format)
  - `04_Divya_Nair.txt` (Plain text format)
- **Relationship**: Semantic paraphrase.
- **Shared Content**:
  - Observations: Both measure a 60-ohm resistor (1.5V to 7.5V readings, ~59.7 ohms).
  - Calculations: Divya paraphrased Chirag's gradient calculation ($59.4$ ohms, $\pm 5\%$ tolerance).
  - Conclusion: Divya reworded Chirag's conclusion preserving identical logical structure and results.
- **Expected Score**: $\ge 0.85$
- **Expected Label**: `"paraphrase"`

---

### 3. Copy Ring (Cluster of 3 Students)
- **Students**:
  - `05_Esha_Gupta.txt`
  - `06_Farhan_Khan.docx` (DOCX format)
  - `07_Gaurav_Mehta.txt`
- **Relationship**: Ring sharing one common source for calculations and conclusion.
- **Shared Content**:
  - Calculations: Identical calculation using $(9.0 - 3.0)/(0.090 - 0.030) = 100.0$ ohms and standard deviation $0.15$ ohms.
  - Conclusion: Identical conclusion text concluding $100.0$ ohms.
  - Observations: Slightly varied trial data (3V to 9V) across the three students.
- **Expected Cluster**:
  - Members: `["05_Esha_Gupta", "06_Farhan_Khan", "07_Gaurav_Mehta"]`
  - Ring Size: 3
  - Internal Pairs: 3 (Esha-Farhan, Farhan-Gaurav, Esha-Gaurav)
  - Expected Pair Scores: $\ge 0.90$
- **Expected Label**: `"likely copy"` or `"shared source"`

---

### 4. Fully Independent Students (Control Group)
The remaining 8 students conducted independent measurements with completely different resistor values, different experimental ranges, distinct calculation methods, and unique phrasing:
- `08_Harini_Iyer.txt` (150-ohm resistor, 1V-5V)
- `09_Ishaan_Reddy.docx` (25-ohm high wattage resistor, 2V-10V)
- `10_Jaya_Mishra.txt` (75-ohm carbon resistor, 1.2V-6.0V)
- `11_Kavya_Pillai.txt` (33-ohm constantan coil, 1V-6V)
- `12_Lokesh_Babu.docx` (120-ohm resistor, 2.4V-12.0V)
- `13_Meera_Sen.txt` (82-ohm resistor, 1.6V-8.0V)
- `14_Nikhil_Deshmukh.txt` (47-ohm resistor, 1V-5V)
- `15_Pooja_Kulkarni.txt` (68-ohm resistor, 2V-10V)

**Expected Result**: None of these students should appear in any flagged pair above the threshold ($0.85$).
