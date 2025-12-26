import os

FILE_PATH = "filter_bot.py"

def fix_file():
    if not os.path.exists(FILE_PATH):
        print("File not found")
        return

    with open(FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    new_lines = []
    fixed_count = 0
    in_cmd_sports = False
    
    for line in lines:
        # 1. Fix Start Message Encoding
        if "Copiar tu ID de cliente" in line and "/id" in line:
            # Always replace to be safe
            new_lines.append('        "🆔 /id » Copiar tu ID de cliente\\n"\n')
            fixed_count += 1
            print("Fixed ID line")
            continue
            
        if "Filtrar tus Deportes" in line and "/deportes" in line:
            new_lines.append('        "🏆 /deportes » Filtrar tus Deportes\\n"\n')
            fixed_count += 1
            print("Fixed Sports line (again to be sure)")
            continue

        # 2. Remove Debug Prints in cmd_sports
        if "async def cmd_sports" in line:
            in_cmd_sports = True
            new_lines.append(line)
            continue
            
        if in_cmd_sports:
            if "async def" in line and "cmd_sports" not in line:
                in_cmd_sports = False # End of function
            
            strip = line.strip()
            if strip.startswith('print("DEBUG:') or strip.startswith('print(f"DEBUG:'):
                fixed_count += 1
                print(f"Removed debug: {strip}")
                continue # Skip line
            if strip.startswith('print(f"ERROR in cmd_sports'):
                fixed_count += 1
                continue
            if strip.startswith('import traceback'):
                fixed_count += 1
                continue
            if strip.startswith('traceback.print_exc'):
                fixed_count += 1
                continue
                
        new_lines.append(line)

    if fixed_count > 0:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"Successfully fixed {fixed_count} lines.")
    else:
        print("No lines needed fixing (or patterns didn't match). check manually.")

if __name__ == "__main__":
    fix_file()
