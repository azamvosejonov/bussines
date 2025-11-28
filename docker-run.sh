#!/bin/bash

# Business Management System - Docker Helper Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker o'rnatilmagan. Iltimos, avval Docker o'rnating."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose o'rnatilmagan. Iltimos, avval Docker Compose o'rnating."
        exit 1
    fi
}

# Setup environment
setup_env() {
    if [ ! -f .env ]; then
        print_info ".env fayl yaratilmoqda..."
        cp .env.example .env
        print_warning ".env faylini ochib, kerakli qiymatlarni kiriting!"
        print_warning "Ayniqsa SECRET_KEY va JWT_SECRET_KEY ni o'zgartiring!"
    else
        print_info ".env fayl allaqachon mavjud"
    fi
}

# Build and start services
start_services() {
    print_info "Docker xizmatlari ishga tushirilmoqda..."
    docker-compose up --build -d
    print_success "Xizmatlar ishga tushirildi!"
    print_info "Ilova http://localhost:5000 manzilida ishlaydi"
}

# Stop services
stop_services() {
    print_info "Docker xizmatlari to'xtatilmoqda..."
    docker-compose down
    print_success "Xizmatlar to'xtatildi!"
}

# Restart services
restart_services() {
    print_info "Docker xizmatlari qayta ishga tushirilmoqda..."
    docker-compose restart
    print_success "Xizmatlar qayta ishga tushirildi!"
}

# Show logs
show_logs() {
    docker-compose logs -f web
}

# Clean up
cleanup() {
    print_warning "Barcha ma'lumotlar o'chiriladi! Davom etish uchun 'yes' kiriting:"
    read -r confirm
    if [ "$confirm" = "yes" ]; then
        print_info "Tozalash boshlandi..."
        docker-compose down -v --rmi all
        rm -rf data/ instance/
        print_success "Toza holatga qaytarildi!"
    else
        print_info "Bekor qilindi."
    fi
}

# Main menu
main_menu() {
    echo
    echo "========================================"
    echo "  Business Management System - Docker"
    echo "========================================"
    echo "1. Ishga tushirish (start)"
    echo "2. To'xtatish (stop)"
    echo "3. Qayta ishga tushirish (restart)"
    echo "4. Loglarni ko'rish (logs)"
    echo "5. Tozalash (cleanup)"
    echo "6. Chiqish (exit)"
    echo "========================================"
    echo -n "Tanlang (1-6): "
}

# Main script
main() {
    check_docker
    setup_env

    while true; do
        main_menu
        read -r choice

        case $choice in
            1)
                start_services
                ;;
            2)
                stop_services
                ;;
            3)
                restart_services
                ;;
            4)
                show_logs
                ;;
            5)
                cleanup
                ;;
            6)
                print_info "Xayr!"
                exit 0
                ;;
            *)
                print_error "Noto'g'ri tanlov. 1-6 orasida raqam kiriting."
                ;;
        esac

        echo
        echo "Davom etish uchun Enter bosing..."
        read -r
    done
}

# Run main function
main "$@"
