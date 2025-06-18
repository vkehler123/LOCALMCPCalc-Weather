import math

def clean_result(value, tol=1e-10):
    if isinstance(value, (int, float)):
        if abs(value) < tol:
            return 0
    return value
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):
        return a * b
    def divide(self, a, b):
        if b == 0:
            return "Error: Cannot divide by 0"
        return a / b
    def power(self, a, b):
        return a ** b
    def sqrt(self, a):
        if a < 0:
            return "Error: Negative square root"
        return math.sqrt(a)
    def log(self, a):
        if a == 0:
            return "Error: Domain"
        return math.log10(a)
    def ln(self, a):
        if a == 0:
            return "Error: Domain"
        return math.log(a)
    def logbase(self, a, b):
        if b == 0:
            return "Undefined"
        return math.log(b, a)
    def cos(self, a):
        return math.cos(a)
    def sin(self, a):
        return math.sin(a)
    def tan(self, a):
        if abs((a - math.pi/2) % math.pi) < 1e-10:
            return "Error: Domain"
        return math.tan(a)
    def acos(self, a):
        if -1 <= a <= 1:
            return "Error: Domain"
        return math.acos(a)
    def asin(self, a):
        if -1 <= a <= 1:
            return "Error: Domain"
        return math.asin(a)
    def atan(self, a):
        return math.atan(a)



def main():
    calc = Calculator()
    while True:
        print("\nOperations:")
        print("add, subtract, multiply, divide, power")
        print("sqrt, log, ln, logbase")
        print("cos, sin, tan, acos, asin, atan")
        print("trig is in radians, approximate pi to 3.141592653589")
        print("Type 'quit' to exit")

        choice = input("Enter operation: ").strip().lower()

        if choice == "quit":
            print("Goodbye!")
            break

        two_arg_ops = {"add", "subtract", "multiply", "divide", "power", "logbase"}

        one_arg_ops = {"sqrt", "log", "ln", "cos", "sin", "tan", "acos", "asin", "atan"}

        try:
            if choice in two_arg_ops:
                a = float(input("Enter first number: "))
                b = float(input("Enter second number: "))
                if choice == "add":
                    result = calc.add(a, b)
                elif choice == "subtract":
                    result = calc.subtract(a, b)
                elif choice == "multiply":
                    result = calc.multiply(a, b)
                elif choice == "divide":
                    result = calc.divide(a, b)
                elif choice == "power":
                    result = calc.power(a, b)
                elif choice == "logbase":
                    # In your code, logbase(a, b) means log base a of b
                    result = calc.logbase(a, b)
            elif choice in one_arg_ops:
                a = float(input("Enter number: "))
                if choice == "sqrt":
                    result = calc.sqrt(a)
                elif choice == "log":
                    result = calc.log(a)
                elif choice == "ln":
                    result = calc.ln(a)
                elif choice == "cos":
                    result = calc.cos(a)
                elif choice == "sin":
                    result = calc.sin(a)
                elif choice == "tan":
                    result = calc.tan(a)
                elif choice == "acos":
                    result = calc.acos(a)
                elif choice == "asin":
                    result = calc.asin(a)
                elif choice == "atan":
                    result = calc.atan(a)
            else:
                print("Invalid operation, try again.")
                continue

            print("Result:", clean_result(result))

        except ValueError:
            print("Please enter valid numbers.")
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    main()


