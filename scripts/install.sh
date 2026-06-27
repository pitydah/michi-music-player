#!/usr/bin/env bash
# ==============================================================================
# Michi Music Player — Unified installer for all Linux distributions
# ==============================================================================
# Auto-detects and installs on:
#   Arch-based: Arch, CachyOS, Manjaro, EndeavourOS, Garuda, Artix
#   Debian-based: Ubuntu, Debian, Linux Mint, Pop!_OS, Elementary, Kali, RPi OS
#   Fedora-based: Fedora, Nobara
#   SUSE-based: openSUSE Tumbleweed, Leap, Gecko
#   (Others with compatible package managers also work via fallback detection)
#
# Usage:
#   ./scripts/install.sh              # Full install
#   ./scripts/install.sh --minimal    # Core only, skip optional deps
#   ./scripts/install.sh --no-venv    # System deps only, skip venv
#   ./scripts/install.sh --dry-run    # Show what would be installed, don't execute
# ==============================================================================
set -euo pipefail

# ── Color output ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

banner()  { echo -e "${BLUE}${BOLD}=== $* ===${NC}"; }
step()    { echo -e "${GREEN}→${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠  $*${NC}"; }
error()   { echo -e "${RED}✗ $*${NC}"; }
success() { echo -e "${GREEN}✓ $*${NC}"; }
detail()  { echo -e "    $*"; }

# ── CLI flags ──
MINIMAL=false
NO_VENV=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --minimal) MINIMAL=true ;;
        --no-venv) NO_VENV=true ;;
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--minimal] [--no-venv] [--dry-run] [--help]"
            echo "  --minimal  Skip optional deps (chromaprint, avahi, portaudio, snapcast)"
            echo "  --no-venv  Install system dependencies only, skip venv creation"
            echo "  --dry-run   Show what would be installed without executing"
            exit 0
            ;;
        *) error "Unknown flag: $arg"; exit 1 ;;
    esac
done

$DRY_RUN && { echo -e "${YELLOW}${BOLD}=== MODO SIMULACIÓN - no se ejecutarán comandos ===${NC}"; echo; }

# ── Dry-run wrapper ──
maybe_run() {
    if $DRY_RUN; then
        echo -e "  ${YELLOW}[DRY-RUN]${NC} $*"
        return 0
    fi
    "$@"
}

# ── Privilege check ──
if ! $DRY_RUN && ! command -v sudo &>/dev/null; then
    error "sudo is required to install system packages"
    exit 1
fi

echo
banner "Michi Music Player — Instalador Unificado"
echo

# ==============================================================================
# Pre-flight checks
# ==============================================================================
preflight_checks() {
    local issues=0

    # Disk space check (need ~500MB for venv + packages)
    local available_kb
    available_kb=$(df -k --output=avail "$HOME" 2>/dev/null | tail -1 || echo "0")
    if [ "$available_kb" -lt 512000 ] 2>/dev/null; then
        warn "Espacio en disco bajo (<500MB disponibles en $HOME)"
        ((issues++))
    fi

    # Check if another package manager is running
    if ! $DRY_RUN; then
        case "$DISTRO" in
            arch)
                if pgrep -x pacman &>/dev/null; then
                    warn "pacman está en ejecución — esperá a que termine otra instalación"
                    ((issues++))
                fi ;;
            debian)
                if pgrep -x apt-get &>/dev/null || pgrep -x dpkg &>/dev/null; then
                    warn "apt/dpkg está en ejecución — esperá a que termine otra instalación"
                    ((issues++))
                fi ;;
            fedora)
                if pgrep -x dnf &>/dev/null; then
                    warn "dnf está en ejecución — esperá a que termine otra instalación"
                    ((issues++))
                fi ;;
            suse)
                if pgrep -x zypper &>/dev/null; then
                    warn "zypper está en ejecución — esperá a que termine otra instalación"
                    ((issues++))
                fi ;;
        esac
    fi

    # Check Python exists
    if ! command -v python3 &>/dev/null; then
        error "python3 no encontrado — instalalo primero con tu gestor de paquetes"
        ((issues++))
    fi

    return "$issues"
}

# ==============================================================================
# STEP 1: Detect distribution
# ==============================================================================
banner "[1/5] Detectando distribución"

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
    else
        error "No se pudo detectar la distribución (falta /etc/os-release)"
        exit 1
    fi

    local id="${ID:-}"
    local id_like="${ID_LIKE:-}"
    local name="${PRETTY_NAME:-$id}"
    local version="${VERSION_ID:-}"

    # Diagnostic output to stderr so stdout returns only the distro key
    echo "  Distribución: $name" >&2
    echo "  ID: $id" >&2
    [ -n "$version" ] && echo "  Versión: $version" >&2

    # Normalize: map known distros to package manager family
    local like="$id $id_like"

    # Arch family
    if [[ "$like" =~ (arch|manjaro|endeavouros|garuda|artix|arcolinux|cachyos) ]]; then
        echo "arch"
        return
    fi

    # Debian family (includes Ubuntu, Mint, Pop, Elementary, Kali, RPi OS, Zorin)
    if [[ "$like" =~ (debian|ubuntu|mint|pop|elementary|kali|neon|zorin|raspbian) ]]; then
        echo "debian"
        return
    fi

    # Fedora family
    if [[ "$like" =~ (fedora|nobara|ultramarine) ]]; then
        echo "fedora"
        return
    fi

    # RHEL family (RHEL, CentOS, Alma, Rocky) — use dnf
    if [[ "$like" =~ (rhel|centos|alma|rocky) ]]; then
        if command -v dnf &>/dev/null; then
            echo "fedora"
            return
        elif command -v yum &>/dev/null; then
            echo "fedora"
            warn "Usando yum como fallback — considerá migrar a dnf"
            return
        fi
    fi

    # SUSE family
    if [[ "$like" =~ (suse|opensuse|gecko) ]]; then
        echo "suse"
        return
    fi

    # Solus
    if [[ "$like" =~ solus ]]; then
        echo "solus"
        return
    fi

    # Void Linux
    if [[ "$like" =~ void ]]; then
        if command -v xbps-install &>/dev/null; then
            echo "void"
            return
        fi
    fi

    # Final fallback: detect by package manager binary
    if command -v pacman &>/dev/null; then
        warn "Distro no reconocida ($name), usando pacman como fallback"
        echo "arch"
    elif command -v apt-get &>/dev/null; then
        warn "Distro no reconocida ($name), usando apt como fallback"
        echo "debian"
    elif command -v dnf &>/dev/null; then
        warn "Distro no reconocida ($name), usando dnf como fallback"
        echo "fedora"
    elif command -v zypper &>/dev/null; then
        warn "Distro no reconocida ($name), usando zypper como fallback"
        echo "suse"
    else
        error "Distribución no soportada: $name"
        echo >&2
        echo "  Soportadas:" >&2
        echo "    Arch, Manjaro, EndeavourOS, Garuda, CachyOS" >&2
        echo "    Ubuntu, Debian, Mint, Pop!_OS, Elementary, Kali" >&2
        echo "    Fedora, Nobara" >&2
        echo "    openSUSE Tumbleweed, Leap, Gecko" >&2
        echo >&2
        echo "  Si tu distro usa alguno de estos gestores de paquetes," >&2
        echo "  debería funcionar. Reportá problemas en:" >&2
        echo "    https://github.com/pitydah/michi-music-player/issues" >&2
        exit 1
    fi
}

DISTRO=$(detect_distro)
success "Familia detectada: $DISTRO"

preflight_checks || {
    error "Las comprobaciones previas fallaron. Corregí los problemas e intentá de nuevo."
    exit 1
}

# ==============================================================================
# STEP 2: Install system dependencies
# ==============================================================================
banner "[2/5] Instalando dependencias del sistema"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# ── Helper: install packages with tolerance for individual failures ──
# Critical packages: script aborts if any fail
# Optional packages: script continues with a warning
install_packages_critical() {
    local pkg_manager="$1"; shift
    local packages=("$@")
    if $DRY_RUN; then
        detail "  [DRY-RUN] $pkg_manager install: ${packages[*]}"
        return 0
    fi
    case "$pkg_manager" in
        pacman) sudo pacman -S --needed --noconfirm "${packages[@]}" ;;
        apt)    sudo apt-get install -y -qq "${packages[@]}" ;;
        dnf)    sudo dnf install -y "${packages[@]}" ;;
        zypper) sudo zypper --non-interactive install -y "${packages[@]}" ;;
    esac
}

install_packages_optional() {
    local pkg_manager="$1"; shift
    local packages=("$@")
    if $DRY_RUN; then
        detail "  [DRY-RUN] $pkg_manager install (optional): ${packages[*]}"
        return 0
    fi
    case "$pkg_manager" in
        pacman) sudo pacman -S --needed --noconfirm "${packages[@]}" 2>/dev/null || true ;;
        apt)    sudo apt-get install -y -qq "${packages[@]}" 2>/dev/null || true ;;
        dnf)    sudo dnf install -y "${packages[@]}" 2>/dev/null || true ;;
        zypper) sudo zypper --non-interactive install -y "${packages[@]}" 2>/dev/null || true ;;
    esac
}

# ── Check if a package is available before trying to install ──
pkg_exists() {
    local pkg_manager="$1" pkg_name="$2"
    case "$pkg_manager" in
        pacman) pacman -Si "$pkg_name" &>/dev/null ;;
        apt)    apt-cache show "$pkg_name" &>/dev/null ;;
        dnf)    dnf info "$pkg_name" &>/dev/null ;;
        zypper) zypper info "$pkg_name" &>/dev/null ;;
        *)      return 1 ;;
    esac
}

# ── Install core packages ──
install_core_deps() {
    local pm
    case "$DISTRO" in
        arch) pm="pacman" ;;
        debian)
            step "Actualizando repositorios..."
            maybe_run sudo apt-get update -qq
            pm="apt"
            ;;
        fedora) pm="dnf" ;;
        suse) pm="zypper" ;;
        *)
            error "Distro '$DISTRO' no soportada para instalación de paquetes"
            exit 1
            ;;
    esac

    step "Instalando paquetes críticos con $pm..."

    case "$DISTRO" in
        arch)
            install_packages_critical "$pm" \
                python python-pip \
                gstreamer gst-plugins-base gst-plugins-good \
                gst-plugins-bad gst-plugins-ugly gst-libav \
                python-gobject python-dbus python-cairo \
                python-mutagen python-numpy
            ;;
        debian)
            install_packages_critical "$pm" \
                python3 python3-pip python3-venv \
                python3-gi gir1.2-gstreamer-1.0 \
                gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
                gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
                gstreamer1.0-libav \
                python3-dbus \
                python3-cairo \
                python3-numpy python3-mutagen
            ;;
        fedora)
            install_packages_critical "$pm" \
                python3 python3-pip python3-devel \
                python3-gobject \
                gstreamer1 gstreamer1-plugins-base gstreamer1-plugins-good \
                gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free \
                gstreamer1-libav \
                python3-dbus python3-cairo \
                python3-numpy python3-mutagen

            # Fedora: check if RPM Fusion's gstreamer1-plugins-ugly is available
            if pkg_exists dnf gstreamer1-plugins-ugly; then
                detail "RPM Fusion detectado — instalando plugins extra..."
                install_packages_optional dnf gstreamer1-plugins-ugly
            else
                detail "RPM Fusion no detectado (plugins -ugly-free alcanzan para reproducción básica)"
                detail "  Para códecs adicionales (AAC, x264):"
                detail "    https://rpmfusion.org/Configuration"
            fi
            ;;
        suse)
            install_packages_critical "$pm" \
                python3 python3-pip python3-devel \
                python3-gobject typelib-1_0-Gst-1_0 \
                gstreamer gstreamer-plugins-base gstreamer-plugins-good \
                gstreamer-plugins-bad gstreamer-plugins-ugly \
                gstreamer-plugins-libav \
                python3-dbus-python python3-cairo \
                python3-numpy python3-mutagen

            # openSUSE: check if Packman repo is configured
            if ! zypper lr -u 2>/dev/null | grep -qi packman; then
                warn "Repositorio Packman no detectado"
                warn "  Para códecs multimedia completos:"
                warn "    Tumbleweed: sudo zypper ar -cfp 90 https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Tumbleweed/ packman"
                warn "    Leap:       sudo zypper ar -cfp 90 https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Leap_\$(grep -oP '(?<=VERSION_ID=)\d+\.\d+' /etc/os-release)/ packman"
            fi
            ;;
    esac
}

# ── Install optional dependencies (graceful failure) ──
install_optional_deps() {
    if $MINIMAL; then
        warn "Modo minimal: omitiendo dependencias opcionales"
        return
    fi

    step "Instalando dependencias opcionales..."

    case "$DISTRO" in
        arch)
            install_packages_optional pacman \
                chromaprint avahi portaudio snapcast
            # PySide6 via system is optional; pip installs the latest anyway
            ;;
        debian)
            install_packages_optional apt \
                libchromaprint-tools avahi-utils portaudio19-dev python3-pyaudio
            # snapcast not in all Debian/Ubuntu repos — try but don't fail
            if pkg_exists apt snapcast; then
                install_packages_optional apt snapcast
            else
                detail "snapcast no disponible en los repositorios (no crítico)"
            fi
            ;;
        fedora)
            install_packages_optional dnf \
                chromaprint-tools avahi-tools portaudio-devel python3-pyaudio
            if pkg_exists dnf snapcast; then
                install_packages_optional dnf snapcast
            else
                detail "snapcast no disponible (no crítico)"
            fi
            ;;
        suse)
            install_packages_optional zypper \
                chromaprint-tools avahi-utils portaudio-devel
            if pkg_exists zypper snapcast; then
                install_packages_optional zypper snapcast
            else
                detail "snapcast no disponible (no crítico)"
            fi
            ;;
    esac

    success "Dependencias opcionales procesadas"
}

install_core_deps
success "Dependencias del sistema instaladas"
install_optional_deps

# ==============================================================================
# STEP 3: Create virtual environment
# ==============================================================================
if $NO_VENV; then
    warn "[3/5] Omitido (--no-venv)"
else
    banner "[3/5] Creando entorno virtual"

    # ── Python version check ──
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
        error "Python >=3.11 requerido. Versión actual: $PY_VERSION"
        if command -v python3.11 &>/dev/null; then
            warn "python3.11 encontrado — usá 'python3.11 -m venv ...' o actualizá tu Python por defecto"
        fi
        exit 1
    fi
    success "Python $PY_VERSION detectado"

    # ── Check PyGObject availability (must come from system) ──
    if ! python3 -c "import gi; gi.require_version('Gst', '1.0')" 2>/dev/null; then
        warn "PyGObject/GStreamer no detectado en el sistema"
        warn "  Esto puede ocurrir si los paquetes del sistema no se instalaron correctamente"
        warn "  Intentando continuar — si falla, verificá: python3-gi, gir1.2-gstreamer-1.0"
    fi

    # ── Create venv ──
    VENV_FLAGS=""
    if python3 -m venv --help 2>&1 | grep -q -- '--system-site-packages'; then
        VENV_FLAGS="--system-site-packages"
    else
        warn "Tu Python no soporta --system-site-packages"
        warn "  PyGObject/DBus/Cairo no serán accesibles desde el venv"
        warn "  Instalá python3-venv o usá un Python más reciente"
    fi

    if [ -d ".venv" ]; then
        warn "Entorno virtual existente (.venv) — se reutilizará"
    else
        step "Creando .venv $VENV_FLAGS..."
        maybe_run python3 -m venv $VENV_FLAGS .venv
        success ".venv creado"
    fi

    # ── Activate venv ──
    if $DRY_RUN; then
        step "[DRY-RUN] Entorno virtual activado (simulado)"
    else
        source .venv/bin/activate
        step "Entorno virtual activado"
    fi

    # ── Upgrade pip ──
    if ! $DRY_RUN; then
        step "Actualizando pip..."
        pip install --upgrade pip --quiet 2>/dev/null || warn "No se pudo actualizar pip (no crítico)"
    fi

    # ==========================================================================
    # STEP 4: Install Python dependencies
    # ==========================================================================
    if $DRY_RUN; then
        banner "[4/5] Dependencias Python (omitido en --dry-run)"
        echo "  [DRY-RUN] Se instalaría:"
        echo "    pip install -e .                               # core (PySide6, mutagen, numpy)"
        echo "    pip install -e '.[dev]'                        # dev (pytest, pytest-qt, ruff)"
        if ! $MINIMAL; then
            echo "    pip install -e '.[recognition]'                # recognition (shazamio, pyaudio)"
        fi
    else
        banner "[4/5] Instalando dependencias Python"

        PIP_FLAGS="--quiet"

        # Core (PySide6, mutagen, numpy)
        step "Instalando Michi Music Player (core)..."
        pip install -e . $PIP_FLAGS || {
            error "Falló la instalación de dependencias core"
            error "  Intentá: pip install PySide6 mutagen numpy"
            error "  Luego: pip install -e ."
            exit 1
        }
        success "Core instalado"

        # Dev (pytest, pytest-qt, ruff)
        step "Instalando dependencias de desarrollo..."
        pip install -e ".[dev]" $PIP_FLAGS || {
            warn "Falló la instalación de dependencias dev (no crítico para ejecutar)"
        }

        # Recognition (shazamio, pyaudio) — optional
        if ! $MINIMAL; then
            step "Instalando dependencias de reconocimiento..."
            pip install -e ".[recognition]" $PIP_FLAGS 2>/dev/null || {
                warn "No se pudieron instalar dependencias de reconocimiento"
                warn "  El reconocimiento de música no estará disponible"
            }
        fi

        success "Dependencias Python instaladas"
    fi
fi

# ==============================================================================
# STEP 5: Desktop integration
# ==============================================================================
banner "[5/5] Integración de escritorio"

LOCAL_BIN="$HOME/.local/bin"
LOCAL_APPS="$HOME/.local/share/applications"
LOCAL_ICONS="$HOME/.local/share/icons/hicolor"
DESKTOP_FILE="$LOCAL_APPS/michi-music-player.desktop"
LAUNCHER_SCRIPT="$LOCAL_BIN/michi-music-player"

# ── Ensure ~/.local/bin exists and is in PATH ──
maybe_run mkdir -p "$LOCAL_BIN"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    warn "~/.local/bin no está en PATH"
    warn "  Agregá esto a tu ~/.bashrc o ~/.profile:"
    warn '    export PATH="$HOME/.local/bin:$PATH"'
    warn "  Luego reiniciá la sesión o ejecutá: source ~/.profile"
fi

# ── Create launcher script ──
if ! $NO_VENV; then
    step "Creando script lanzador en ~/.local/bin..."
    if $DRY_RUN; then
        detail "[DRY-RUN] Escribiría $LAUNCHER_SCRIPT"
    else
        cat > "$LAUNCHER_SCRIPT" << LAUNCHER_EOF
#!/usr/bin/env bash
# Michi Music Player launcher — auto-activates the virtual environment
REPO_DIR="$REPO_DIR"
if [ ! -f "\$REPO_DIR/.venv/bin/activate" ]; then
    echo "Error: virtual environment not found at \$REPO_DIR/.venv" >&2
    echo "Please re-run: \$REPO_DIR/scripts/install.sh" >&2
    exit 1
fi
source "\$REPO_DIR/.venv/bin/activate"
exec michi-music-player "\$@"
LAUNCHER_EOF
        chmod +x "$LAUNCHER_SCRIPT"
    fi
    success "Lanzador creado: $LAUNCHER_SCRIPT"
fi

# ── Install desktop file ──
step "Instalando .desktop file..."
maybe_run mkdir -p "$LOCAL_APPS"
if $DRY_RUN; then
    detail "[DRY-RUN] Instalaría $DESKTOP_FILE"
elif ! $NO_VENV; then
    sed "s|^Exec=.*|Exec=$LAUNCHER_SCRIPT|" \
        data/michi-music-player.desktop > "$DESKTOP_FILE"
else
    cp data/michi-music-player.desktop "$DESKTOP_FILE"
fi

if ! $DRY_RUN && command -v desktop-file-validate &>/dev/null; then
    desktop-file-validate "$DESKTOP_FILE" 2>/dev/null || \
        warn "El .desktop file tiene advertencias (no críticas)"
fi
success ".desktop instalado en $DESKTOP_FILE"

# ── Install icons ──
step "Instalando iconos FreeDesktop (hicolor)..."
if $DRY_RUN; then
    detail "[DRY-RUN] Instalaría iconos multi-resolución en $LOCAL_ICONS"
elif ! $NO_VENV && [ -f scripts/install_icons.py ]; then
    python3 scripts/install_icons.py 2>/dev/null || {
        warn "Falló la generación de iconos multi-resolución"
        warn "  Instalando fallback: icono 256x256..."
        mkdir -p "$LOCAL_ICONS/256x256/apps"
        cp icons/app_icon.png "$LOCAL_ICONS/256x256/apps/michi-music-player.png"
    }
else
    mkdir -p "$LOCAL_ICONS/256x256/apps"
    cp icons/app_icon.png "$LOCAL_ICONS/256x256/apps/michi-music-player.png"
fi

# ── Update desktop & icon caches ──
step "Actualizando cachés del sistema..."
if $DRY_RUN; then
    detail "[DRY-RUN] Ejecutaría update-desktop-database + gtk-update-icon-cache + kbuildsycoca"
elif ! $DRY_RUN; then
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$LOCAL_APPS" 2>/dev/null && \
            success "update-desktop-database" || true
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$LOCAL_ICONS" 2>/dev/null && \
            success "gtk-update-icon-cache" || true
    fi
    # KDE Plasma: rebuild menu cache
    for kbuild in kbuildsycoca6 kbuildsycoca5; do
        if command -v "$kbuild" &>/dev/null; then
            "$kbuild" 2>/dev/null && success "$kbuild (KDE menu)" || true
            break
        fi
    done
fi

# ── Symlink for direct terminal access ──
if ! $NO_VENV && ! $DRY_RUN; then
    step "Creando acceso rápido en ~/.local/bin..."
    maybe_run ln -sf "$REPO_DIR/.venv/bin/michi-music-player" "$LOCAL_BIN/michi-music-player-venv" 2>/dev/null || true
elif ! $NO_VENV && $DRY_RUN; then
    detail "[DRY-RUN] Crearía symlink en $LOCAL_BIN/michi-music-player-venv"
fi

success "Integración de escritorio completada"

# ==============================================================================
# Verification
# ==============================================================================
echo
banner "Verificando instalación"

if ! $NO_VENV && [ -f scripts/check_runtime.py ] && ! $DRY_RUN; then
    python3 scripts/check_runtime.py 2>/dev/null || {
        warn "Verificación con advertencias — probablemente funcionalidades opcionales"
    }
elif $DRY_RUN; then
    detail "[DRY-RUN] Verificación omitida"
else
    warn "Verificación omitida (check_runtime.py requiere venv activo)"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo
banner "Instalación completa"
echo
echo "  Michi Music Player está listo:"
echo
if $NO_VENV; then
    echo "    Terminal:  michi-music-player"
else
    echo "    Terminal:  source .venv/bin/activate && michi-music-player"
    echo "    Directo:   ~/.local/bin/michi-music-player"
fi
echo "    Menú app:  Buscá 'Michi Music Player' en tu menú de aplicaciones"
echo
if ! $NO_VENV; then
    echo "  Para desarrollo:"
    echo "    pytest tests/ -q     # ejecutar tests (suite completa)"
    echo "    ruff check .         # verificar lint (0 esperado)"
    echo "    python -m compileall -q -x '.venv/|\\.tmpl\\.' .  # verificar compilación"
fi
if $DRY_RUN; then
    echo
    warn "Esto fue una simulación. Ejecutá sin --dry-run para instalar."
fi
echo
