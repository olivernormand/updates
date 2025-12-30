import tempfile
import threading
import time
from pathlib import Path

import click
import httpx
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from .config import settings


def get_client() -> httpx.Client:
    return httpx.Client(base_url=settings.api_base_url, timeout=60.0)


def start_server_background() -> threading.Thread:
    """Start the API server in a background thread."""
    import uvicorn
    from .api import app

    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    for _ in range(50):
        try:
            with httpx.Client() as client:
                client.get("http://localhost:8000/health", timeout=0.5)
                return thread
        except Exception:
            time.sleep(0.1)

    return thread


def record_until_keypress(sample_rate: int = 44100) -> np.ndarray:
    """Record audio until Enter is pressed. Returns audio data."""
    chunks = []
    recording = True

    def callback(indata, frames, time_info, status):
        if recording:
            chunks.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", callback=callback):
        input()  # Wait for Enter
        recording = False

    if chunks:
        return np.concatenate(chunks, axis=0)
    return np.array([], dtype="int16")


def process_audio(audio_data: np.ndarray, sample_rate: int = 44100) -> None:
    """Process recorded audio through the API pipeline."""
    if len(audio_data) == 0:
        click.secho("No audio recorded.", fg="yellow")
        return

    duration = len(audio_data) / sample_rate
    click.echo(f"Recorded {duration:.1f}s of audio. Processing...")

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wavfile.write(f.name, sample_rate, audio_data)
        temp_path = Path(f.name)

    try:
        with get_client() as client:
            with open(temp_path, "rb") as audio_file:
                response = client.post(
                    "/process",
                    files={"audio": ("recording.wav", audio_file, "audio/wav")},
                )

        if response.status_code == 200:
            data = response.json()
            click.echo("")
            highlight = data["highlight"]
            title = highlight.get("title") or "Unknown"
            author = highlight.get("author")
            source = f"{title}" + (f" by {author}" if author else "")
            click.secho(f"[{source}]", fg="cyan", bold=True)
            click.echo(f"  {highlight['text']}")
            if highlight.get("note"):
                click.secho(f"  Note: {highlight['note']}", fg="yellow")
            click.secho(f"  → Saved to Readwise (ID: {data.get('readwise_id')})", fg="green")
        else:
            click.secho(f"Error: {response.text}", fg="red")

    finally:
        temp_path.unlink()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Updates CLI - Voice-to-Readwise capture tool."""
    if ctx.invoked_subcommand is None:
        # Default command: start interactive mode
        ctx.invoke(start)


@cli.command()
@click.option("--context", "-c", "ctx_text", help="Set reading context before starting")
def start(ctx_text: str | None):
    """Start interactive recording session (default command)."""
    click.secho("Updates - Voice to Readwise", fg="cyan", bold=True)
    click.echo("")

    # Start server
    click.echo("Starting server...")
    start_server_background()
    click.secho("Server ready.", fg="green")
    click.echo("")

    # Set context if provided
    if ctx_text:
        with get_client() as client:
            client.put("/context", json={"context": ctx_text})
        click.echo(f"Context: {ctx_text}")
        click.echo("")

    click.echo("Press [Enter] to start recording, [Enter] again to stop.")
    click.echo("Press [Ctrl+C] to exit.")
    click.echo("")

    try:
        while True:
            click.secho("Ready. Press [Enter] to record...", fg="yellow")
            input()

            click.secho("● Recording... Press [Enter] to stop.", fg="red", bold=True)
            audio_data = record_until_keypress()

            process_audio(audio_data)
            click.echo("")

    except KeyboardInterrupt:
        click.echo("\nGoodbye!")


@cli.command()
@click.option("--duration", "-d", default=10, help="Recording duration in seconds")
@click.option("--sample-rate", "-s", default=44100, help="Audio sample rate")
def record(duration: int, sample_rate: int):
    """Record audio for a fixed duration."""
    click.echo(f"Recording for {duration} seconds...")

    try:
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        click.echo("Recording complete.")

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wavfile.write(f.name, sample_rate, audio_data)
            temp_path = Path(f.name)

        click.echo("Processing...")

        with get_client() as client:
            with open(temp_path, "rb") as audio_file:
                response = client.post(
                    "/process",
                    files={"audio": ("recording.wav", audio_file, "audio/wav")},
                )

        temp_path.unlink()

        if response.status_code == 200:
            data = response.json()
            click.echo("\n" + "=" * 50)
            click.echo(f"Transcript: {data['transcript']}")
            click.echo("=" * 50)
            highlight = data["highlight"]
            click.echo(f"Title: {highlight.get('title', 'N/A')}")
            click.echo(f"Author: {highlight.get('author', 'N/A')}")
            click.echo(f"Text: {highlight['text']}")
            click.echo("=" * 50)
            click.secho("Saved to Readwise!", fg="green")
        else:
            click.secho(f"Error: {response.text}", fg="red")

    except KeyboardInterrupt:
        click.echo("\nRecording cancelled.")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")


@cli.command()
@click.argument("text", required=False)
def context(text: str | None):
    """Get or set current reading/listening context."""
    with get_client() as client:
        if text:
            response = client.put("/context", json={"context": text})
            if response.status_code == 200:
                click.secho(f"Context set: {text}", fg="green")
            else:
                click.secho(f"Error: {response.text}", fg="red")
        else:
            response = client.get("/context")
            if response.status_code == 200:
                data = response.json()
                if data.get("context"):
                    click.echo(f"Current context: {data['context']}")
                else:
                    click.echo("No context set.")
            else:
                click.secho(f"Error: {response.text}", fg="red")


@cli.command()
def recent():
    """Show recent submissions."""
    with get_client() as client:
        response = client.get("/recent")
        if response.status_code == 200:
            data = response.json()
            if data["count"] == 0:
                click.echo("No recent submissions.")
            else:
                click.echo(f"Recent submissions ({data['count']}):\n")
                click.echo(data["context_string"])
        else:
            click.secho(f"Error: {response.text}", fg="red")


@cli.command()
@click.argument("audio_path", type=click.Path(exists=True))
def transcribe(audio_path: str):
    """Transcribe an audio file."""
    with get_client() as client:
        with open(audio_path, "rb") as f:
            response = client.post(
                "/transcribe",
                files={"audio": (Path(audio_path).name, f)},
            )

        if response.status_code == 200:
            data = response.json()
            click.echo(f"Transcript: {data['text']}")
        else:
            click.secho(f"Error: {response.text}", fg="red")


@cli.command()
@click.argument("text")
@click.option("--no-context", is_flag=True, help="Don't include recent context")
def parse(text: str, no_context: bool):
    """Parse text into a structured highlight."""
    with get_client() as client:
        response = client.post(
            "/parse",
            json={"text": text, "include_recent_context": not no_context},
        )

        if response.status_code == 200:
            data = response.json()
            highlight = data["highlight"]
            click.echo(f"Title: {highlight.get('title', 'N/A')}")
            click.echo(f"Author: {highlight.get('author', 'N/A')}")
            click.echo(f"Text: {highlight['text']}")
            click.echo(f"Confidence: {data['confidence']:.0%}")
        else:
            click.secho(f"Error: {response.text}", fg="red")


@cli.command()
def health():
    """Check API health."""
    with get_client() as client:
        try:
            response = client.get("/health")
            if response.status_code == 200:
                data = response.json()
                click.echo(f"Status: {data['status']}")
                for service, ok in data["services"].items():
                    status = click.style("OK", fg="green") if ok else click.style("FAIL", fg="red")
                    click.echo(f"  {service}: {status}")
            else:
                click.secho(f"API error: {response.text}", fg="red")
        except httpx.ConnectError:
            click.secho(f"Cannot connect to API at {settings.api_base_url}", fg="red")


@cli.command()
def serve():
    """Start the API server (foreground)."""
    click.echo(f"Starting server at {settings.api_base_url}...")
    from .api import run
    run()


if __name__ == "__main__":
    cli()
