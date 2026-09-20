import html
from html.parser import HTMLParser


ALLOWED_TAGS = {"p", "br", "strong", "em", "ul", "ol", "li"}
TAG_ALIASES = {"b": "strong", "i": "em", "div": "p"}
VOID_TAGS = {"br"}
HTML_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
DROP_CONTENT_TAGS = {"script", "style", "template", "iframe", "object", "embed"}


def plain_text_to_html(value):
    """Convert unformatted input into safe paragraphs without losing line breaks."""
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        return ""
    paragraphs = normalized.split("\n\n")
    return "".join(
        f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>"
        for paragraph in paragraphs
    )


class _SafeRichTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.stack = []
        self.blocked_stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.blocked_stack:
            if tag not in HTML_VOID_TAGS:
                self.blocked_stack.append(tag)
            return
        if tag in DROP_CONTENT_TAGS:
            if tag not in HTML_VOID_TAGS:
                self.blocked_stack.append(tag)
            return
        tag = TAG_ALIASES.get(tag, tag)
        if tag not in ALLOWED_TAGS:
            return
        self.output.append(f"<{tag}>")
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if self.blocked_stack or tag.lower() in DROP_CONTENT_TAGS:
            return
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.blocked_stack:
            while self.blocked_stack:
                blocked_tag = self.blocked_stack.pop()
                if blocked_tag == tag:
                    break
            return
        tag = TAG_ALIASES.get(tag, tag)
        if tag not in self.stack:
            return
        while self.stack:
            open_tag = self.stack.pop()
            self.output.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data):
        if not self.blocked_stack:
            self.output.append(html.escape(data))

    def close(self):
        super().close()
        while self.stack:
            self.output.append(f"</{self.stack.pop()}>")


def sanitize_rich_text(value):
    """Return HTML containing only formatting tags with no attributes or URLs."""
    parser = _SafeRichTextParser()
    parser.feed(str(value or ""))
    parser.close()
    return "".join(parser.output).strip()


class _PlainTextParser(HTMLParser):
    BLOCK_TAGS = {"p", "br", "li", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "li":
            self.output.append("\n- ")
        elif tag.lower() in self.BLOCK_TAGS:
            self.output.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.BLOCK_TAGS:
            self.output.append("\n")

    def handle_data(self, data):
        self.output.append(data)


def rich_text_to_plain_text(value):
    parser = _PlainTextParser()
    parser.feed(str(value or ""))
    parser.close()
    lines = [line.rstrip() for line in "".join(parser.output).splitlines()]
    collapsed = []
    for line in lines:
        if line or (collapsed and collapsed[-1]):
            collapsed.append(line)
    rendered = "\n".join(collapsed).strip()
    while "\n\n- " in rendered:
        rendered = rendered.replace("\n\n- ", "\n- ")
    return rendered
