# Maintainer install script for ERIS AI
# Instala iconos, desktop entry, y limpia up

post_install() {
    # Actualizar base de datos de desktop entries
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database >/dev/null 2>&1 || true
    fi

    echo ""
    echo "✅ ERIS AI instalado correctamente."
    echo ""
    echo "📌 Para ejecutar:"
    echo "   • Desde el menú de aplicaciones: ERIS AI"
    echo "   • Desde terminal: eris"
    echo ""
    echo "📌 Primera ejecución:"
    echo "   La primera vez se instalarán las dependencias Python automáticamente."
    echo "   Esto puede tomar varios minutos. Ten paciencia."
    echo ""
    echo "📌 Configuración:"
    echo "   • Edita config/api_keys.json para configurar API keys y dispositivos"
    echo "   • Edita config/eris_config.json para configuración general"
    echo ""
    echo "📌 Documentación:"
    echo "   • /usr/share/doc/eris/README.md"
    echo "   • /usr/share/doc/eris/AGENTS.md"
    echo ""
}

post_remove() {
    # Limpiar desktop database si ERIS es el único entry eliminado
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database >/dev/null 2>&1 || true
    fi
}

post_upgrade() {
    # Conservar configuración del usuario
    :
}
