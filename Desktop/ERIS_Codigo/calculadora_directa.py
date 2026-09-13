
import tkinter as tk

def evaluate(event):
    try:
        result.set(eval(entry.get()))
    except Exception as e:
        result.set("Error")

root = tk.Tk()
root.title("Calculadora")
root.geometry("300x150")

entry = tk.Entry(root, textvariable=tk.StringVar())
entry.bind("<Return>", evaluate)
entry.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

result = tk.StringVar()
result.set("Resultado")
label = tk.Label(root, textvariable=result)
label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

root.mainloop()
