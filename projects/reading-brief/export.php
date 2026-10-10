<?php
declare(strict_types=1);

// Run inside the FreshRSS container as its web user. Reads entries only.
require '/var/www/FreshRSS/cli/_cli.php';
$options = getopt('', ['user:', 'days:', 'limit:']);
if (empty($options['user'])) {
    fail('Pass --user with the FreshRSS username');
}
cliInitUser($options['user']);
$days = filter_var($options['days'] ?? '7', FILTER_VALIDATE_INT);
$limit = filter_var($options['limit'] ?? '1000', FILTER_VALIDATE_INT);
if ($days === false || $days < 1 || $days > 30 || $limit === false || $limit < 1 || $limit > 5000) {
    fail('days must be 1-30 and limit must be 1-5000');
}
$feeds = FreshRSS_Factory::createFeedDao()->listFeeds();
$entries = FreshRSS_Factory::createEntryDao()->listWhere(
    state: FreshRSS_Entry::STATE_NOT_READ,
    id_min: (string)(time() - $days * 86400) . '000000',
    limit: $limit,
);
foreach ($entries as $entry) {
    $feed = $feeds[$entry->feedId()] ?? null;
    echo json_encode([
        'id' => (string)$entry->id(), 'title' => $entry->title(),
        'source' => $feed?->name() ?? '', 'url' => $entry->link(),
        'published' => $entry->date(raw: true), 'is_read' => $entry->isRead(),
        'content_html' => $entry->content(),
    ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), "\n";
}
