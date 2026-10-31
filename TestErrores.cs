using System;

public class TestErrores 
{
    public void MetodoConErrores()
    {
        string nombre = "Eris";
        int valor = 10;

        if (valor = 10) // Error de compilación: '=' en lugar de '=='
        {
            Console.WriteLine("Valor incorrecto");
        }
    }
}