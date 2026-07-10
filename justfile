# List available recipes
default:
    @just --list

# Render all AsciiDoc files to standalone HTML
build:
    asciidoctor *.adoc

# Remove rendered HTML
clean:
    rm -f *.html
