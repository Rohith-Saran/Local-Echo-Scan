"""Sample data generator for Local Echo Scan.

Generates 15 realistic student lab records for "Verification of Ohm's Law"
plus a lab manual in sample_data/output/.

Planted test cases:
1. Direct Copy: 01_Aditya_Sharma.txt and 02_Bhavna_Patel.txt
2. Paraphrase / Reworded: 03_Chirag_Verma.docx and 04_Divya_Nair.txt
3. Copy Ring (size 3): 05_Esha_Gupta.txt, 06_Farhan_Khan.docx, 07_Gaurav_Mehta.txt
4. Independent: 08_Harini_Iyer through 15_Pooja_Kulkarni
"""

from __future__ import annotations

import os
from pathlib import Path
from docx import Document

# Shared Template Paragraphs
AIM = (
    "Aim: To verify Ohm's law by establishing the relationship between the potential "
    "difference across a given metallic conductor and the electric current flowing through it, "
    "and to determine the unknown resistance of the resistor by plotting a V-I graph."
)

APPARATUS = (
    "Apparatus Required: A DC regulated power supply (0-15V), a digital DC voltmeter (0-20V), "
    "a digital DC ammeter (0-500mA), an unknown wire-wound resistor, a variable rheostat (0-100 ohms), "
    "a one-way plug key, and insulated connecting copper wires."
)

PROCEDURE = (
    "Procedure: Clean the ends of the connecting wires using sandpaper and assemble the circuit "
    "as per the circuit schematic. Connect the voltmeter in parallel across the resistor specimen "
    "and the ammeter in series with the battery and rheostat. Close the circuit key and adjust the "
    "rheostat slider to record initial values of voltage V and current I. Increase the potential "
    "systematically in regular increments, taking simultaneous readings on both meters at each step. "
    "Plot a graph with potential difference on the y-axis and current on the x-axis to calculate "
    "the slope representing resistance."
)

TEMPLATE_PARAGRAPHS = [AIM, APPARATUS, PROCEDURE]


# Students Data Definitions
STUDENTS = [
    # --- Case 1: Direct Copy Pair (Aditya & Bhavna) ---
    {
        "filename": "01_Aditya_Sharma.txt",
        "format": "txt",
        "observations": (
            "Observation and Tabulation: The readings obtained from the circuit were recorded as follows: "
            "At applied voltage 2.0 V, current was 0.040 A. At voltage 4.0 V, current was 0.081 A. "
            "At voltage 6.0 V, current was 0.120 A. At voltage 8.0 V, current was 0.159 A. "
            "At voltage 10.0 V, current was 0.201 A. The average ratio of V/I yields an empirical "
            "resistance value of approximately 49.8 ohms."
        ),
        "calculations": (
            "Calculations: From the linear regression slope of the V-I plot: "
            "Slope = Delta V / Delta I = (10.0 - 2.0) / (0.201 - 0.040) = 8.0 / 0.161 = 49.69 ohms. "
            "The percentage deviation from the nominal 50-ohm resistor is approximately 0.62%."
        ),
        "conclusion": (
            "Conclusion: The experiment successfully verified Ohm's Law. The V-I characteristic curve "
            "was a straight line passing through the origin, confirming that the current flowing through "
            "the resistor is directly proportional to the applied voltage. The experimental resistance was "
            "found to be 49.7 ohms."
        ),
    },
    {
        "filename": "02_Bhavna_Patel.txt",
        "format": "txt",
        # Exact copy of Aditya
        "observations": (
            "Observation and Tabulation: The readings obtained from the circuit were recorded as follows: "
            "At applied voltage 2.0 V, current was 0.040 A. At voltage 4.0 V, current was 0.081 A. "
            "At voltage 6.0 V, current was 0.120 A. At voltage 8.0 V, current was 0.159 A. "
            "At voltage 10.0 V, current was 0.201 A. The average ratio of V/I yields an empirical "
            "resistance value of approximately 49.8 ohms."
        ),
        "calculations": (
            "Calculations: From the linear regression slope of the V-I plot: "
            "Slope = Delta V / Delta I = (10.0 - 2.0) / (0.201 - 0.040) = 8.0 / 0.161 = 49.69 ohms. "
            "The percentage deviation from the nominal 50-ohm resistor is approximately 0.62%."
        ),
        "conclusion": (
            "Conclusion: The experiment successfully verified Ohm's Law. The V-I characteristic curve "
            "was a straight line passing through the origin, confirming that the current flowing through "
            "the resistor is directly proportional to the applied voltage. The experimental resistance was "
            "found to be 49.7 ohms."
        ),
    },

    # --- Case 2: Reworded Paraphrase (Chirag & Divya) ---
    {
        "filename": "03_Chirag_Verma.docx",
        "format": "docx",
        "observations": (
            "Observations: Measurements recorded across the rheostat stages were: "
            "1.5V produced 0.025A; 3.0V produced 0.051A; 4.5V produced 0.076A; "
            "6.0V produced 0.100A; 7.5V produced 0.126A. The resistance computed "
            "at individual points averaged 59.7 ohms."
        ),
        "calculations": (
            "Calculations: Calculating resistance using graph slope: "
            "R = Delta V / Delta I = (7.5 - 1.5) / (0.126 - 0.025) = 6.0 / 0.101 = 59.4 ohms. "
            "Theoretical tolerance was specified as +/- 5%."
        ),
        "conclusion": (
            "Conclusion: Ohm's Law is verified as the ratio of potential difference to current "
            "remained constant throughout the voltage range. The resistance of the unknown conductor "
            "is determined to be 59.4 ohms with high precision."
        ),
    },
    {
        "filename": "04_Divya_Nair.txt",
        "format": "txt",
        # Paraphrased calculations and conclusion from Chirag
        "observations": (
            "Observations: Trial readings obtained during testing were: "
            "1.5 V gave 0.025 A; 3.0 V gave 0.051 A; 4.5 V gave 0.076 A; "
            "6.0 V gave 0.100 A; 7.5 V gave 0.126 A. Individual V/I quotients averaged 59.7 ohms."
        ),
        "calculations": (
            "Calculations: Determining the resistance through the plot gradient: "
            "R = Delta V / Delta I = (7.5 - 1.5) / (0.126 - 0.025) = 6.0 / 0.101 = 59.4 ohms. "
            "Manufacturer component tolerance was specified as +/- 5%."
        ),
        "conclusion": (
            "Conclusion: Ohm's Law was successfully verified since the quotient of voltage over current "
            "remained steady across the entire operating range. The unknown conductor resistance was "
            "evaluated as 59.4 ohms with high precision."
        ),
    },

    # --- Case 3: Ring of 3 Students (Esha, Farhan, Gaurav) ---
    {
        "filename": "05_Esha_Gupta.txt",
        "format": "txt",
        "observations": (
            "Observations: Applied voltage was varied between 3.0V and 9.0V in steps of 1.5V. "
            "At 3.0V current was 0.030A; at 4.5V current was 0.045A; at 6.0V current was 0.061A; "
            "at 7.5V current was 0.074A; at 9.0V current was 0.090A."
        ),
        "calculations": (
            "Calculations: The slope of the line of best fit gives the experimental resistance: "
            "R = (V2 - V1) / (I2 - I1) = (9.0 - 3.0) / (0.090 - 0.030) = 6.0 / 0.060 = 100.0 ohms. "
            "The standard deviation across repeated trial runs was 0.15 ohms."
        ),
        "conclusion": (
            "Conclusion: Ohm's Law is substantiated because the graph of potential difference against "
            "electric current forms a straight line crossing the origin. The resistance of the wire specimen "
            "was found to be exactly 100.0 ohms."
        ),
    },
    {
        "filename": "06_Farhan_Khan.docx",
        "format": "docx",
        "observations": (
            "Observations: Stepping the potential from 3.0V to 9.0V in 1.5V intervals gave current values: "
            "0.030A at 3V, 0.045A at 4.5V, 0.060A at 6V, 0.075A at 7.5V, and 0.090A at 9V."
        ),
        # Shared source calculations & conclusion with Esha & Gaurav
        "calculations": (
            "Calculations: The slope of the line of best fit gives the experimental resistance: "
            "R = (V2 - V1) / (I2 - I1) = (9.0 - 3.0) / (0.090 - 0.030) = 6.0 / 0.060 = 100.0 ohms. "
            "The standard deviation across repeated trial runs was 0.15 ohms."
        ),
        "conclusion": (
            "Conclusion: Ohm's Law is substantiated because the graph of potential difference against "
            "electric current forms a straight line crossing the origin. The resistance of the wire specimen "
            "was found to be exactly 100.0 ohms."
        ),
    },
    {
        "filename": "07_Gaurav_Mehta.txt",
        "format": "txt",
        "observations": (
            "Observations: For applied voltages between 3V and 9V in increments of 1.5V, the current meter "
            "read 0.031A, 0.045A, 0.060A, 0.076A, and 0.090A respectively."
        ),
        # Shared source calculations & conclusion with Esha & Farhan
        "calculations": (
            "Calculations: The slope of the line of best fit gives the experimental resistance: "
            "R = (V2 - V1) / (I2 - I1) = (9.0 - 3.0) / (0.090 - 0.030) = 6.0 / 0.060 = 100.0 ohms. "
            "The standard deviation across repeated trial runs was 0.15 ohms."
        ),
        "conclusion": (
            "Conclusion: Ohm's Law is substantiated because the graph of potential difference against "
            "electric current forms a straight line crossing the origin. The resistance of the wire specimen "
            "was found to be exactly 100.0 ohms."
        ),
    },

    # --- Independent Students (08 - 15) ---
    {
        "filename": "08_Harini_Iyer.txt",
        "format": "txt",
        "observations": (
            "Observations: Using a 150-ohm test resistor, the power supply was adjusted from 1.0V to 5.0V. "
            "Readings: 1.0V -> 0.0067A, 2.0V -> 0.0134A, 3.0V -> 0.0199A, 4.0V -> 0.0267A, 5.0V -> 0.0335A."
        ),
        "calculations": (
            "Calculations: Resistance determined by reciprocal conductance: R = 1 / slope(I vs V). "
            "Calculated resistance = 5.0 / 0.0335 = 149.25 ohms. Error margin = 0.5%."
        ),
        "conclusion": (
            "Conclusion: Experimental findings demonstrate that conductor current scales linearly with "
            "voltage up to 5V, verifying Ohm's relation with 149.3 ohms resistance."
        ),
    },
    {
        "filename": "09_Ishaan_Reddy.docx",
        "format": "docx",
        "observations": (
            "Observations: A 25-ohm high-wattage resistor was evaluated across 2V to 10V. "
            "Amperage observed: 0.080A at 2V, 0.160A at 4V, 0.239A at 6V, 0.318A at 8V, 0.399A at 10V."
        ),
        "calculations": (
            "Calculations: Regression analysis of data pairs yielded R = 25.06 ohms with R-squared of 0.9998. "
            "Joule heating was negligible at these current levels."
        ),
        "conclusion": (
            "Conclusion: Linear response was retained across high current injection. Ohm's law holds valid "
            "with measured resistor value 25.1 ohms."
        ),
    },
    {
        "filename": "10_Jaya_Mishra.txt",
        "format": "txt",
        "observations": (
            "Observations: Potential difference applied across unknown carbon resistor: "
            "1.2V gave 0.016A, 2.4V gave 0.032A, 3.6V gave 0.048A, 4.8V gave 0.065A, 6.0V gave 0.080A."
        ),
        "calculations": (
            "Calculations: Mean resistance R = sum(V_i / I_i) / 5 = (75.0 + 75.0 + 75.0 + 73.8 + 75.0) / 5 = 74.76 ohms."
        ),
        "conclusion": (
            "Conclusion: Constant proportionality between voltage drop and current indicates pure ohmic "
            "behavior. Measured resistance is 74.8 ohms."
        ),
    },
    {
        "filename": "11_Kavya_Pillai.txt",
        "format": "txt",
        "observations": (
            "Observations: Constantan wire coil tested with voltage range 1V to 6V in 1V increments. "
            "Currents recorded: 0.030A, 0.061A, 0.091A, 0.122A, 0.151A, 0.182A."
        ),
        "calculations": (
            "Calculations: Plotting V on y-axis and I on x-axis gave line gradient = 32.96 ohms. "
            "Temperature remained steady throughout."
        ),
        "conclusion": (
            "Conclusion: The constantan wire specimen obeys Ohm's law with an empirical resistance "
            "of 33.0 ohms."
        ),
    },
    {
        "filename": "12_Lokesh_Babu.docx",
        "format": "docx",
        "observations": (
            "Observations: Testing a 120-ohm nominal resistor: Applied 2.4V (0.020A), 4.8V (0.040A), "
            "7.2V (0.060A), 9.6V (0.081A), and 12.0V (0.100A)."
        ),
        "calculations": (
            "Calculations: Delta V / Delta I = (12.0 - 2.4) / (0.100 - 0.020) = 9.6 / 0.080 = 120.0 ohms. "
            "Zero offset calibration was accounted for."
        ),
        "conclusion": (
            "Conclusion: The metallic resistor behaves as an ideal ohmic device. Value confirmed as 120.0 ohms."
        ),
    },
    {
        "filename": "13_Meera_Sen.txt",
        "format": "txt",
        "observations": (
            "Observations: Voltmeter and ammeter pairs: (1.6V, 0.019A), (3.2V, 0.039A), (4.8V, 0.058A), "
            "(6.4V, 0.078A), (8.0V, 0.098A)."
        ),
        "calculations": (
            "Calculations: Resistance R = (8.0 - 1.6) / (0.098 - 0.019) = 6.4 / 0.079 = 81.01 ohms. "
            "Color code on resistor indicated 82 ohms."
        ),
        "conclusion": (
            "Conclusion: Experimental verification succeeded within 1.2% of color code nominal value. "
            "Ohm's relationship confirmed."
        ),
    },
    {
        "filename": "14_Nikhil_Deshmukh.txt",
        "format": "txt",
        "observations": (
            "Observations: Stepwise voltage settings and observed current: 1.0V (0.021A), 2.0V (0.042A), "
            "3.0V (0.064A), 4.0V (0.085A), 5.0V (0.106A)."
        ),
        "calculations": (
            "Calculations: Least squares slope = 47.17 ohms. Standard uncertainty calculated as +/- 0.3 ohms."
        ),
        "conclusion": (
            "Conclusion: Direct proportionality verified. The resistor exhibits constant resistance of 47.2 ohms."
        ),
    },
    {
        "filename": "15_Pooja_Kulkarni.txt",
        "format": "txt",
        "observations": (
            "Observations: Circuit readings with 68-ohm test component: 2.0V -> 0.029A, 4.0V -> 0.059A, "
            "6.0V -> 0.088A, 8.0V -> 0.118A, 10.0V -> 0.147A."
        ),
        "calculations": (
            "Calculations: Ratio V/I slope: R = (10.0 - 2.0) / (0.147 - 0.029) = 8.0 / 0.118 = 67.80 ohms. "
            "Nominal rating: 68 ohms."
        ),
        "conclusion": (
            "Conclusion: Ohm's law is verified with high accuracy. Experimental resistance: 67.8 ohms."
        ),
    },
]


def generate_sample_dataset(output_dir: Path | str | None = None) -> Path:
    """Generate all sample student files and lab manual."""
    if output_dir is None:
        base_dir = Path(__file__).resolve().parent
        output_dir = base_dir / "output"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write lab manual
    manual_path = output_dir / "lab_manual.txt"
    manual_content = "\n\n".join(TEMPLATE_PARAGRAPHS)
    manual_path.write_text(manual_content, encoding="utf-8")
    print(f"Generated lab manual: {manual_path.name}")

    # 2. Write each student record
    for student in STUDENTS:
        filename = student["filename"]
        file_path = output_dir / filename
        fmt = student["format"]

        all_paragraphs = TEMPLATE_PARAGRAPHS + [
            student["observations"],
            student["calculations"],
            student["conclusion"],
        ]

        if fmt == "txt":
            content = "\n\n".join(all_paragraphs)
            file_path.write_text(content, encoding="utf-8")
        elif fmt == "docx":
            doc = Document()
            for p_text in all_paragraphs:
                doc.add_paragraph(p_text)
            doc.save(str(file_path))

        print(f"Generated [{fmt.upper()}]: {filename}")

    print(f"\nAll 15 sample records + lab manual successfully created in {output_dir}")
    return output_dir


if __name__ == "__main__":
    generate_sample_dataset()
