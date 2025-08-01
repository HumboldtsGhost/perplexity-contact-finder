"""
Output Selection Module - Interactive output format selection and file access guidance
"""
import os
from pathlib import Path
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import questionary
from datetime import datetime
import subprocess
import platform

console = Console()

class OutputSelector:
    """Handles output format selection and provides access guidance"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def select_output_formats(self) -> List[str]:
        """Interactive output format selection"""
        console.print("\n[bold]📁 Choose Output Formats[/bold]")
        console.print("[dim]Select all the formats you want to export:[/dim]\n")
        
        # Format descriptions
        format_info = {
            "csv": {
                "name": "CSV (Spreadsheet)",
                "desc": "Standard spreadsheet format - opens in Excel, Google Sheets",
                "icon": "📊"
            },
            "excel": {
                "name": "Excel Workbook (.xlsx)",
                "desc": "Formatted Excel file with colors and styling",
                "icon": "📈"
            },
            "txt": {
                "name": "Text File",
                "desc": "Human-readable format with detailed sources - opens in any text editor",
                "icon": "📝"
            },
            "json": {
                "name": "JSON (Technical)",
                "desc": "Complete data for developers and technical analysis",
                "icon": "🔧"
            },
            "apollo": {
                "name": "Apollo CSV",
                "desc": "Special format for Apollo.io CRM import",
                "icon": "🚀"
            }
        }
        
        # Create choices with descriptions
        choices = []
        for key, info in format_info.items():
            choices.append(
                questionary.Choice(
                    title=f"{info['icon']} {info['name']} - {info['desc']}",
                    value=key,
                    checked=(key in ['csv', 'excel', 'txt'])  # Default selections
                )
            )
        
        selected = questionary.checkbox(
            "Select formats (use Space to select/deselect, Enter to confirm):",
            choices=choices
        ).ask()
        
        if not selected:
            console.print("[yellow]No formats selected. Defaulting to CSV and Text.[/yellow]")
            return ['csv', 'txt']
            
        return selected
    
    def show_file_access_guide(self, exported_files: Dict[str, str]):
        """Show users how to access their exported files"""
        console.print("\n[bold green]✅ Export Complete![/bold green]\n")
        
        # Create a nice table of exported files
        table = Table(title="📁 Your Exported Files", show_lines=True)
        table.add_column("Format", style="cyan", width=15)
        table.add_column("Filename", style="white", width=35)
        table.add_column("How to Open", style="dim", width=40)
        
        # Get the full output directory path
        output_path = self.output_dir.absolute()
        
        # Add rows for each exported file
        for format_type, filepath in exported_files.items():
            filename = os.path.basename(filepath)
            
            if format_type == 'csv':
                how_to = "Excel, Google Sheets, or any spreadsheet app"
            elif format_type == 'excel':
                how_to = "Microsoft Excel or Google Sheets"
            elif format_type == 'txt':
                how_to = "Notepad, TextEdit, or any text editor"
            elif format_type == 'json':
                how_to = "VS Code, Notepad++, or browser"
            elif format_type == 'apollo':
                how_to = "Import into Apollo.io CRM"
            else:
                how_to = "Any compatible application"
                
            table.add_row(format_type.upper(), filename, how_to)
        
        console.print(table)
        
        # Show location panel
        location_panel = Panel(
            f"[bold]Location:[/bold] {output_path}\n\n"
            f"[dim]All files are saved in the 'output' folder inside the Contact Finder directory[/dim]",
            title="📂 Where to Find Your Files",
            border_style="green"
        )
        console.print(location_panel)
        
        # Platform-specific instructions
        system = platform.system()
        
        if system == "Darwin":  # macOS
            console.print("\n[bold]🖥️  Mac: How to Open Your Files[/bold]")
            console.print("1. Open Finder")
            console.print("2. Navigate to the perplexity-contact-finder folder")
            console.print("3. Open the 'output' folder")
            console.print("4. Double-click any file to open it")
            console.print("\n[dim]Tip: Press Cmd+Space and search for 'output' to find it quickly[/dim]")
            
        elif system == "Windows":
            console.print("\n[bold]🖥️  Windows: How to Open Your Files[/bold]")
            console.print("1. Open File Explorer")
            console.print("2. Navigate to the perplexity-contact-finder folder")
            console.print("3. Open the 'output' folder")
            console.print("4. Double-click any file to open it")
            console.print("\n[dim]Tip: You can search for the filename in the Start menu[/dim]")
            
        else:  # Linux
            console.print("\n[bold]🖥️  Linux: How to Open Your Files[/bold]")
            console.print("1. Open your file manager")
            console.print("2. Navigate to the perplexity-contact-finder folder")
            console.print("3. Open the 'output' folder")
            console.print("4. Double-click any file to open it")
        
        # Ask if user wants to open the folder
        if questionary.confirm("\n📂 Would you like to open the output folder now?", default=True).ask():
            self.open_output_folder()
    
    def open_output_folder(self):
        """Open the output folder in the system file explorer"""
        try:
            system = platform.system()
            output_path = str(self.output_dir.absolute())
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", output_path])
            elif system == "Windows":
                subprocess.run(["explorer", output_path])
            else:  # Linux
                subprocess.run(["xdg-open", output_path])
                
            console.print("[green]✓ Output folder opened![/green]")
            
        except Exception as e:
            console.print(f"[yellow]Couldn't open folder automatically. Please navigate to:[/yellow]")
            console.print(f"[cyan]{self.output_dir.absolute()}[/cyan]")
    
    def show_quick_stats(self, contacts: List, selected_formats: List[str]):
        """Show a quick summary before export"""
        console.print("\n[bold]📊 Export Summary[/bold]")
        
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="dim")
        stats_table.add_column("Value", style="bold")
        
        stats_table.add_row("Total contacts to export:", f"[green]{len(contacts)}[/green]")
        stats_table.add_row("Contacts with email:", f"[green]{sum(1 for c in contacts if c.primary_email)}[/green]")
        stats_table.add_row("Contacts with phone:", f"[green]{sum(1 for c in contacts if c.primary_phone)}[/green]")
        stats_table.add_row("Output formats selected:", f"[cyan]{', '.join(f.upper() for f in selected_formats)}[/cyan]")
        
        console.print(stats_table)
        console.print()
    
    def export_with_options(self, contacts: List, exporter) -> Dict[str, str]:
        """Export contacts with user-selected formats"""
        # Let user select formats
        selected_formats = self.select_output_formats()
        
        # Show quick stats
        self.show_quick_stats(contacts, selected_formats)
        
        # Export in selected formats
        exported_files = {}
        
        with console.status("[bold green]Exporting files...") as status:
            if 'csv' in selected_formats:
                status.update("Exporting CSV...")
                exported_files['csv'] = exporter.export_to_csv(contacts)
                
            if 'excel' in selected_formats:
                status.update("Exporting Excel...")
                exported_files['excel'] = exporter.export_to_excel(contacts)
                
            if 'txt' in selected_formats:
                status.update("Exporting Text...")
                exported_files['txt'] = exporter.export_to_txt(contacts)
                
            if 'json' in selected_formats:
                status.update("Exporting JSON...")
                exported_files['json'] = exporter.export_to_json(contacts)
                
            if 'apollo' in selected_formats:
                status.update("Exporting Apollo CSV...")
                exported_files['apollo'] = exporter.export_to_apollo_csv(contacts)
        
        return exported_files