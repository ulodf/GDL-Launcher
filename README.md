# Gallery-DL Launcher

A feature-rich GUI application for managing multiple instances of [gallery-dl](https://github.com/mikf/gallery-dl), a command-line downloader for image galleries and collections.

## Features

- **Multi-instance Downloads**: Run multiple gallery-dl instances simultaneously with different configurations
- **Unified Logging**: View logs from all instances in a single interface
- **Download History**: Track all downloads with statistics and export capability
- **Browser Integration**: Receive URLs directly from your web browser
- **URL Management**: Easily load, save, and paste download URLs
- **Flexible Configuration**: Set global options, per-instance settings, and content filters

## Requirements

- Python 3.8 or higher
- gallery-dl installed (see setup instructions)
- Tkinter (usually comes with Python)

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install gallery-dl if not already installed:

```bash
pip install gallery-dl
```

## Usage

### Basic Usage

1. Run the application:

```bash
python gallery_dl_launcher.py
```

2. Paste URLs into an instance tab
3. Configure output directory and options
4. Click "Run" to start downloading

### Browser Integration

The application includes a local web server that listens on port 6580 by default. You can send URLs directly to the application using:

- The included `extension_receiver.html` page
- A browser extension configured to send URLs to this port

### Configuration

- **Global Options**: Set common gallery-dl options in the Config tab
- **Per-Instance Settings**: Each instance tab has its own configuration
- **History**: View download history and statistics in the History tab

## File Locations

The application stores configuration and data in the following locations:

- Configuration: `~/.gallery_dl_launcher.cfg`
- Data directory: `~/.gallery_dl_launcher/`
- Archive files: `~/.gallery_dl_launcher/archive_instance_X.txt`

## License

This project is open source software.

## Acknowledgements

This project uses [gallery-dl](https://github.com/mikf/gallery-dl) as its backend.
