# Gallery-DL Launcher

A feature-rich GUI application for managing multiple instances of [gallery-dl](https://github.com/mikf/gallery-dl), a command-line downloader for image galleries and collections.

## Features

- **Multi-instance Downloads**: Run multiple gallery-dl instances simultaneously with different configurations
- **Unified Logging**: View logs from all instances in a single interface
- **Bulk Actions**: Start or stop all instances at once with a single click
- **URL Checking & Distribution**: Check if URLs exist in any instance and automatically distribute URLs to maintain balanced instances
- **Content Type Filtering**: Choose to download only images, only videos, or both for each instance
- **Temporary Directory for .part Files**: Store in-progress downloads in a separate directory
- **Per-instance Download Archives**: Track downloaded files separately for each instance to avoid duplicates
- **State Persistence**: Application remembers its state, including number of instances and all URLs
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
python gallery_dl_launcher_new.py
```

2. Paste URLs into an instance tab
3. Configure output directory and options
4. Click "Start Download" to begin downloading

### Content Type Filtering

1. In each instance tab, you'll see checkboxes for "Download Images" and "Download Videos"
2. Check or uncheck to control which content types are downloaded
3. For example, uncheck "Download Images" and keep "Download Videos" checked to download only videos

### Temporary Directory for .part Files

1. Each instance has a configurable temporary directory for in-progress downloads
2. By default, this is set to a "temp" folder inside your output directory
3. Files remain in this directory until download completes, then move to the final destination

### URL Checking and Distribution

1. Use the "URL Checker" tab to check if URLs exist in any instance
2. You can add a single URL to the best instance (with fewest URLs)
3. Distribute multiple URLs across all instances to maintain balanced downloads

### Bulk Actions

1. Use the buttons at the top of the application to start or stop all instances at once
2. You can also access these features from the "Instances" menu

### Configuration

- **Global Options**: Set common gallery-dl options in the Global Config tab
- **Per-Instance Settings**: Each instance tab has its own configuration for output directory, temporary directory, and download archive file
- **Archive Files**: Each instance uses its own download archive file to track downloaded URLs and prevent duplicates

## File Locations

The application stores configuration and data in the following locations:

- Configuration: `~/.gallery_dl_launcher.cfg`
- Data directory: `~/.gallery_dl_launcher/`
- Instance settings: `~/.gallery_dl_launcher/instances/instance_X.json`
- Saved URLs: `~/.gallery_dl_launcher/links/instance_X_links.txt`
- Archive files: `~/.gallery_dl_launcher/archives/instance_X_archive.txt`
- Application state: `~/.gallery_dl_launcher/state/app_state.json`

## License

This project is open source software.

## Acknowledgements

This project uses [gallery-dl](https://github.com/mikf/gallery-dl) as its backend.
