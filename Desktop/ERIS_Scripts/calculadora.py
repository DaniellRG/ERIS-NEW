class Calculadora:
    """
    Clase que realiza operaciones básicas de una calculadora.
    """

    def sumar(self, a: float, b: float) -> float:
        """
        Realiza la suma de dos números.

        Args:
            a (float): Primer número.
            b (float): Segundo número.

        Returns:
            float: Resultado de la suma.
        """
        return a + b

    def restar(self, a: float, b: float) -> float:
        """
        Realiza la resta de dos números.

        Args:
            a (float): Primer número.
            b (float): Segundo número.

        Returns:
            float: Resultado de la resta.
        """
        return a - b

    def multiplicar(self, a: float, b: float) -> float:
        """
        Realiza la multiplicación de dos números.

        Args:
            a (float): Primer número.
            b (float): Segundo número.

        Returns:
            float: Resultamiento de la multiplicación.
        """
        return a * b

    def dividir(self, a: float, b: float) -> float:
        """
        Realiza la división de dos números.

        Args:
            a (float): Primer número.
            b (float): Segundo número.

        Returns:
            float: Resultado de la división.
        """
        try:
            return a / b
        except ZeroDivisionError:
            raise ValueError("No se puede dividir entre cero")


def main():
    """
    Función principal que ejecuta el programa.
    """
    calc = Calculadora()
    try:
        num1 = float(input("Ingrese el primer número: "))
        num2 = float(input("Ingrese el segundo número: "))
        operacion = input("Seleccione operación (sumar/restar/multiplicar/dividir): ").strip().lower()

        if operacion == "sumar":
            resultado = calc.sumar(num1, num2)
        elif operacion == "restar":
            resultado = calc.restar(num1, num2)
        elif operacion == "multiplicar":
            resultado = calc.multiplicar(num1, num2)
        elif operacion == "dividir":
            resultado = calc.dividir(num1, num2)
        else:
            raise ValueError("Operación inválida")

        print(f"Resultado: {resultado}")
    except ValueError as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()