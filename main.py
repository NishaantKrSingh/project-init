import yaml
import typer
import questionary
import subprocess
import pexpect # For advanced interactivity
import sys
from rich.console import Console
from rich.panel import Panel

# Initialize Rich console for beautiful printing
console = Console()

def load_recipes(file_path: str = "recipes.yaml"):
    """Loads the command recipes from a YAML file."""
    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[bold red]Error: The file '{file_path}' was not found.[/bold red]")
        raise typer.Exit()

def run_command_simple(command, cwd=None):
    """Executes a command and streams its output, letting the user interact."""
    console.print(Panel(f"[bold cyan]Running:[/bold cyan] [yellow]{command}[/yellow]", title="Executing Command", border_style="green"))
    # Using subprocess.run and inheriting stdio allows for direct user interaction
    process = subprocess.run(
        command,
        shell=True,
        cwd=cwd, # Change directory if specified
        check=False # We will check the return code manually
    )
    if process.returncode != 0:
        console.print(f"[bold red]Error: Command failed with exit code {process.returncode}[/bold red]")
        return False
    return True

def run_command_interactive(command, interactions, cwd=None):
    """Executes a command and automates interactive prompts using pexpect."""
    console.print(Panel(f"[bold cyan]Running (automated):[/bold cyan] [yellow]{command}[/yellow]", title="Executing Command", border_style="blue"))
    try:
        child = pexpect.spawn(command, cwd=cwd, encoding='utf-8', timeout=300)
        # Log the output to the console so the user can see what's happening
        child.logfile_read = sys.stdout

        for interaction in interactions:
            child.expect(interaction['question'], timeout=60)
            child.sendline(interaction['answer'])

        # Wait for the command to finish
        child.expect(pexpect.EOF)
        child.close()

        if child.exitstatus != 0:
            console.print(f"[bold red]Error: Automated command failed with exit code {child.exitstatus}[/bold red]")
            return False
        return True

    except pexpect.exceptions.TIMEOUT:
        console.print("[bold red]Error: A prompt was not found in time (timeout). The command may have changed.[/bold red]")
        return False
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred with pexpect: {e}[/bold red]")
        return False


def main():
    """
    A CLI tool to automate repetitive project setup commands.
    """
    console.print("[bold green]Project Setup Automator 🚀[/bold green]")
    recipes = load_recipes()

    # Let the user choose a recipe using questionary
    recipe_name = questionary.select(
        "Which project setup recipe would you like to run?",
        choices=[recipe['name'] for recipe in recipes]
    ).ask()

    if not recipe_name:
        return # User cancelled

    # Find the selected recipe
    selected_recipe = next((r for r in recipes if r['name'] == recipe_name), None)

    # Ask for arguments if any are defined
    args_values = {}
    if 'args' in selected_recipe:
        for arg_def in selected_recipe['args']:
            arg_name, question = list(arg_def.items())[0]
            value = questionary.text(question).ask()
            if not value:
                console.print("[bold red]Project name cannot be empty. Aborting.[/bold red]")
                return
            args_values[arg_name] = value

    # Execute the commands
    for i, command_step in enumerate(selected_recipe['commands']):
        step_name = command_step['name']
        command_to_run = command_step['run']
        
        # Replace placeholders like {{project_name}} with actual values
        for arg_name, arg_value in args_values.items():
            command_to_run = command_to_run.replace(f"{{{{{arg_name}}}}}", arg_value)

        # Get the working directory for the command
        cwd = command_step.get('cwd')
        if cwd:
            for arg_name, arg_value in args_values.items():
                cwd = cwd.replace(f"{{{{{arg_name}}}}}", arg_value)

        console.print(f"\n[bold]Step {i+1}/{len(selected_recipe['commands'])}: {step_name}[/bold]")
        
        # Decide which execution function to use
        if 'interactive' in command_step:
            success = run_command_interactive(command_to_run, command_step['interactive'], cwd=cwd)
        else:
            success = run_command_simple(command_to_run, cwd=cwd)
        
        if not success:
            console.print("[bold red]A step failed. Aborting recipe.[/bold red]")
            break # Stop executing if a command fails
        else:
            console.print(f"[bold green]✅ Step '{step_name}' completed successfully.[/bold green]")

    else: # This 'else' belongs to the 'for' loop, runs if the loop completed without a 'break'
        console.print("\n[bold green]🎉 All steps completed successfully! Your project is ready.[/bold green]")


if __name__ == "__main__":
    typer.run(main)