import csv
with open("test_logs.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow([0.0] * 44)   # flux normal
    writer.writerow([10.0] * 44)  # flux attaque
    writer.writerow([0.0] * 44)   # flux normal