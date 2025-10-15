def print_intro():
    """Display the welcome screen with ASCII art."""
    # ANSI color codes
    ORANGE = "\033[38;5;208m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Clear screen effect with some spacing
    print("\n" * 2)
    
    # Welcome box with orange border
    box_width = 50
    welcome_text = "Welcome to GORD by pingintel"
    padding = (box_width - len(welcome_text) - 2) // 2
    
    print(f"{ORANGE}{'═' * box_width}{RESET}")
    print(f"{ORANGE}║{' ' * padding}{BOLD}{welcome_text}{RESET}{ORANGE}{' ' * (box_width - len(welcome_text) - padding - 2)}║{RESET}")
    print(f"{ORANGE}{'═' * box_width}{RESET}")
    print()
    
    # ASCII art for GORD in block letters (financial terminal style)
    gord_art = f"""{BOLD}{ORANGE}
 ██████╗  ██████╗ ██████╗ ██████╗ 
██╔════╝ ██╔═══██╗██╔══██╗██╔══██╗
██║  ███╗██║   ██║██████╔╝██║  ██║
██║   ██║██║   ██║██╔══██╗██║  ██║
╚██████╔╝╚██████╔╝██║  ██║██████╔╝
 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═════╝ 
{RESET}"""
    
    print(gord_art)
    print()
    print("Your AI assistant for E&S.")
    print("Learn more at: www.pingintel.com")
    print()
    print("Ask me any questions. Type 'exit' or 'quit' to end.")
    print()