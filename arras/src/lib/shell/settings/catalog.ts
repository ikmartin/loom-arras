// What Settings holds: its sections, in two groups, and every setting's name and what it does, which the rows draw their words from. Each section says where its settings are kept.

export type Group = 'loom' | 'quilt';
export type SectionId = 'profile' | 'appearance' | 'files' | 'general' | 'documents' | 'agents' | 'library' | 'problems' | 'overleaf';

export interface Section {
	id: SectionId;
	label: string;
	group: Group;
	/** Where its settings are kept, said under the page's title. */
	where: string;
	/** An icon's path data on a 24-unit square, stroked. */
	icon: string;
}

export interface Setting {
	id: string;
	section: SectionId;
	name: string;
	/** What it does; `code` spans in backticks. */
	what: string;
	/** Where it is written, as config.toml names it. */
	key?: string;
}

export const GROUPS: { id: Group; label: string }[] = [
	{ id: 'loom', label: 'Loom' },
	{ id: 'quilt', label: 'Quilt' }
];

const BROWSER = 'Kept in this browser only.';
const QUILT = "Saved in this quilt's config.toml, shared with everyone who has the quilt. Only you change it; an agent cannot.";

export const SECTIONS: Section[] = [
	{ id: 'profile', label: 'Profile', group: 'loom', where: 'Kept for you on this computer, for every quilt.', icon: 'M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8M4 21a8 8 0 0 1 16 0' },
	{ id: 'appearance', label: 'Appearance', group: 'loom', where: BROWSER, icon: 'M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4' },
	{ id: 'files', label: 'Files', group: 'loom', where: `${BROWSER} What Docs shows of the project.`, icon: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z' },
	{ id: 'general', label: 'General', group: 'quilt', where: QUILT, icon: 'M4 6h16M4 12h16M4 18h10' },
	{ id: 'documents', label: 'Documents', group: 'quilt', where: QUILT, icon: 'M7 3h7l5 5v13H7zM14 3v5h5' },
	{ id: 'agents', label: 'Agents', group: 'quilt', where: QUILT, icon: 'M7 7h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-6a3 3 0 0 1 3-3M12 3v4M9 13h.01M15 13h.01' },
	{ id: 'library', label: 'Library', group: 'quilt', where: QUILT, icon: 'M5 4v16M9 4v16M13 5l4 15M19 4l-2 16' },
	{ id: 'problems', label: 'Problems', group: 'quilt', where: QUILT, icon: 'M12 3l9 16H3zM12 10v4M12 17h.01' },
	{ id: 'overleaf', label: 'Overleaf', group: 'quilt', where: 'The pairing is kept in .loom/, on this computer.', icon: 'M4 12a8 8 0 0 1 14-5M20 12a8 8 0 0 1-14 5M18 3v4h-4M6 21v-4h4' }
];

export const SETTINGS: Setting[] = [
	{ id: 'face', section: 'appearance', name: 'Typeface', what: 'The face documents and notes are set in.' },
	{ id: 'size', section: 'appearance', name: 'Size', what: 'The body size, everywhere text is read.' },
	{ id: 'width', section: 'appearance', name: 'Width', what: 'How wide a line runs before it wraps.' },
	{ id: 'theme', section: 'appearance', name: 'Theme', what: "Auto follows this computer's light or dark setting." },
	{ id: 'format', section: 'appearance', name: 'Document format', what: 'How a document and its results are set: the compiled paper, continuous or in its pages, or a column for reading on screen, narrow or wide.' },
	{ id: 'comments', section: 'appearance', name: 'Annotations open', what: 'Floating opens a box over the text at its mark; inline opens it in place.' },
	{ id: 'ids', section: 'appearance', name: 'Show ids', what: "Each result's id and state in the left margin, for working on the quilt rather than reading it." },
	{ id: 'hide-aux', section: 'files', name: 'Hide aux LaTeX files', what: 'Leave out what a compile writes for its next run: `.aux`, `.log`, `.synctex.gz`, `.bbl` and the rest. The compiled PDF stays.' },
	{ id: 'author', section: 'profile', name: 'Your name', what: 'Who your acceptances and annotations are recorded as. A different name selects a different review history.', key: '[author] name' },
	{ id: 'quilt.name', section: 'general', name: 'Name', what: 'What the quilt is called, at the top of the column.', key: '[quilt] name' },
	{ id: 'quilt.prefix', section: 'general', name: 'Id prefix', what: "Starts every new result's id.", key: '[quilt] prefix' },
	{ id: 'quilt.engine', section: 'general', name: 'TeX engine', what: "The default; a document's own `% !TEX program` line wins.", key: '[quilt] engine' },
	{ id: 'quilt.history', section: 'general', name: 'History folder', what: 'Where loom keeps every recorded version and landmark.', key: '[quilt] history' },
	{ id: 'quilt.home', section: 'documents', name: 'Front door', what: "What the viewer opens when you have nothing open. Unset, the quilt's README.", key: '[quilt] home' },
	{ id: 'quilt.main', section: 'documents', name: 'Default document', what: 'The LaTeX document loom compiles and reads macros from when the quilt holds several.', key: '[quilt] main' },
	{ id: 'quilt.research_state', section: 'documents', name: 'Research state', what: 'The page an agent keeps on where the work stands, and you edit.', key: '[quilt] research_state' },
	{ id: 'agents.deny', section: 'agents', name: 'Where agents may not write', what: "Patterns as in `.gitignore`, from the quilt's top. An agent edits every other file in place, and you keep or undo its changes in Review.", key: '[agents] deny' },
	{ id: 'agents.protected', section: 'agents', name: 'Always protected', what: "Loom's records, this file and the research state, which an agent writes only through loom." },
	{ id: 'agents.apps', section: 'agents', name: 'Apps', what: 'Which agent apps start loom here. Claude Code refuses a denied path itself; the others are told the list, and loom still refuses their writes through it.' },
	{ id: 'library.online', section: 'library', name: 'Use the network', what: 'Let the library look identifiers up (zbMATH Open, Crossref) and fetch papers from arXiv. Off, it uses only what is on this computer.', key: '[library] online' },
	{ id: 'library.contact', section: 'library', name: 'Contact address', what: 'Given to the lookup services, as they ask.', key: '[library] contact' },
	{ id: 'lint.disable', section: 'problems', name: 'Silenced', what: 'Problems loom no longer reports for this quilt.', key: '[lint] disable' },
	{ id: 'sync', section: 'overleaf', name: 'Overleaf project', what: "The clone of a Git workspace, such as an Overleaf project, that coauthors edit. Loom runs Git only in that folder, and never changes the quilt's files without you." }
];

export const SECTION = Object.fromEntries(SECTIONS.map((s) => [s.id, s])) as Record<SectionId, Section>;
export const SETTING = Object.fromEntries(SETTINGS.map((s) => [s.id, s])) as Record<string, Setting>;

