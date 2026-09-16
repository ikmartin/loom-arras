// Routes. Keys may contain / and #; they travel in the rest segment of /node/, with # percent-encoded.
export function nodeUrl(key: string): string {
	return '/node/' + key.split('/').map(encodeURIComponent).join('/');
}

export function keyFromParam(param: string): string {
	return param.split('/').map(decodeURIComponent).join('/');
}

export function masterUrl(path: string): string {
	const stem = path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
	return '/master/' + encodeURIComponent(stem);
}

export function masterStem(path: string): string {
	return path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
}

export function digestUrl(citekey: string): string {
	return '/digest/' + encodeURIComponent(citekey);
}

export function tagUrl(tag: string): string {
	return '/tag/' + encodeURIComponent(tag);
}

export function taxonUrl(slug: string): string {
	return '/taxon/' + encodeURIComponent(slug);
}

export function threadUrl(id: string): string {
	return '/thread/' + encodeURIComponent(id);
}
