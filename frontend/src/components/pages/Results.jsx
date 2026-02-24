import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import "primereact/resources/themes/lara-light-indigo/theme.css";
import { useEffect, useState } from "react";
import { Box, Button, Grid, IconButton, Tooltip, Typography } from "@mui/material";
import ThumbUpOffAltIcon from "@mui/icons-material/ThumbUpOffAlt";
import ThumbDownOffAltIcon from "@mui/icons-material/ThumbDownOffAlt";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { MetadataFilters, SearchBar } from "../common";
import { getBM25Data, submitFeedback } from "../../api";
import { displayColumns } from "../../utils";
import { useNavigate } from "react-router-dom";
import humanizeDuration from "humanize-duration";

const normalize = (s) => (s || "").replace(/\s+/g, " ").trim();

// Map start/end in normalized string back to original text character positions
function normalizedToOriginalPositions(text, normStart, normEnd) {
    let ni = 0;
    let inSpace = false;
    let start = -1;
    let end = -1;
    for (let i = 0; i < text.length; i++) {
        if (/\s/.test(text[i])) {
            if (!inSpace) { inSpace = true; ni++; }
        } else {
            inSpace = false;
            ni++;
        }
        if (start === -1 && ni >= normStart) start = i;
        if (end === -1 && ni >= normEnd) { end = i + 1; break; }
    }
    if (end === -1) end = text.length;
    return { start: start < 0 ? 0 : start, end };
}

// Escape for regex (simple)
function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Split by query terms and wrap matches in <mark>
function highlightQueryTermsSimple(segment, query) {
    if (!segment || !query || !String(query).trim()) return segment;
    const terms = String(query).trim().split(/\s+/).filter((w) => w.length > 0);
    if (terms.length === 0) return segment;
    const re = new RegExp(`(${terms.map(escapeRe).join("|")})`, "gi");
    const parts = segment.split(re);
    return parts.map((p, i) => (i % 2 === 1 ? <mark key={i} style={{ backgroundColor: "rgba(255, 193, 7, 0.5)", padding: "0 1px" }}>{p}</mark> : p));
}

// Hybrid: chunk gets light background; query terms get highlight (mark)
function NarrativeWithHighlightAndChunk({ narrative, snippet, query }) {
    const text = narrative == null ? "" : String(narrative);
    if (!text) return "";
    const nText = normalize(text);
    const nSnippet = (snippet && normalize(snippet)) || "";
    const idx = nSnippet ? nText.toLowerCase().indexOf(nSnippet.toLowerCase()) : -1;
    const hasChunk = idx >= 0;
    const pos = hasChunk ? normalizedToOriginalPositions(text, idx, idx + nSnippet.length) : { start: 0, end: 0 };
    const beforeChunk = text.slice(0, pos.start);
    const chunkText = hasChunk ? text.slice(pos.start, pos.end) : "";
    const afterChunk = hasChunk ? text.slice(pos.end) : text;
    return (
        <>
            {highlightQueryTermsSimple(beforeChunk, query)}
            {chunkText ? (
                <span style={{ backgroundColor: "rgba(255, 235, 59, 0.25)", fontWeight: 600 }}>
                    {highlightQueryTermsSimple(chunkText, query)}
                </span>
            ) : null}
            {highlightQueryTermsSimple(afterChunk, query)}
        </>
    );
}

export const Results = () => {
    const navigate = useNavigate();

    const [loading, setLoading] = useState(false);
    const [searchResults, setSearchResults] = useState([]);
    const [allResults, setAllResults] = useState([]);
    const [totalResults, setTotalResults] = useState(-1);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageLength, setPageLength] = useState(10);
    const [userQuery, setUserQuery] = useState("");
    const [queryTime, setQueryTime] = useState(-1.0);
    const [queryTimeText, setQueryTimeText] = useState("");
    const [filters, setFilters] = useState({ when_prefix: "", where_contains: "", anomaly_contains: "" });
    const [feedbackSent, setFeedbackSent] = useState({}); // { `${docId}`: true|false } so we can show "Thanks"

    const onSubmit = () => {
        const query = localStorage.getItem("user-query");
        if (query) {
            setLoading(true);
            const startQueryTime = performance.now();
            const filterParams = {};
            if (filters.when_prefix) filterParams.when_prefix = filters.when_prefix;
            if (filters.where_contains) filterParams.where_contains = filters.where_contains;
            if (filters.anomaly_contains) filterParams.anomaly_contains = filters.anomaly_contains;
            getBM25Data(query, filterParams)
                .then((x) => {
                    setAllResults(x);
                    setTotalResults(x.length);
                    setSearchResults(x.slice(0, pageLength));
                })
                .finally(() => {
                    setLoading(false);
                    setUserQuery(query);
                    setQueryTime(performance.now() - startQueryTime);
                });
        } else {
            navigate("/");
        }
    };

    const onPage = (event) => {
        const page = event.page;
        const start = page * pageLength;
        const end = start + pageLength;
        setCurrentPage(page);
        setSearchResults(allResults.slice(start, end));
    };

    // Load initial results
    useEffect(() => {
        onSubmit();
    }, []);

    useEffect(() => {
        setCurrentPage(0);
        if (allResults.length) setSearchResults(allResults.slice(0, pageLength));
    }, [userQuery, totalResults]);

    // Update query time text every time query time updates
    useEffect(() => {
        setQueryTimeText(humanizeDuration(queryTime, {
            round: true,
            units: ["s", "ms"]
        }));
    }, [queryTime]);

    return <>
        <Box
            sx={{
                display: 'flex', 
                flexDirection: "column",
                textAlign: "center",
            }}
        >
            <Grid 
                container 
                rowSpacing={3 }
                sx={{ 
                    // backgroundColor: '#f8f9fa',
                    mt: "5dvh",
                }}
            >
                {/* Home + About */}
                <Grid size={1}>
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", justifyContent: "center" }}>
                        <Button onClick={() => navigate("/")}>Home</Button>
                        <Button onClick={() => navigate("/about")}>About</Button>
                    </Box>
                </Grid>

                {/* Search bar */}
                <Grid size = {8}>
                    <Box
                        sx = {{
                            width: "80%",
                            alignItems: "center",
                            ml: "10%"
                        }}
                    >
                        <SearchBar
                            disabled={loading}
                            onSubmit={onSubmit}
                            initQuery={userQuery}
                        />
                    </Box>
                </Grid>

                {/* Metadata filters button */}
                <Grid size = {3}>
                    <Box
                        sx={{
                            float: "left"
                        }}
                    >
                        <MetadataFilters
                            disabled={loading}
                            filters={filters}
                            onFiltersChange={setFilters}
                            onApply={onSubmit}
                        />
                    </Box>
                </Grid>

                {/* Results table */}
                <Grid size={12}>
                    {/* Loading spinner while waiting on search */}
                    {loading && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: { xs: 3, sm: "50px" }, width: '100%' }}>
                            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
                                <div className="spinner-border" style={{ width: "5rem", height: "5rem" }} role="status">
                                    <span className="sr-only"></span>
                                </div>
                            </div>
                        </Box>
                    )}

                    {/* Results table once search is complete */}
                    {!loading && (
                        <Box>
                            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 1, mb: 1 }}>
                                <Typography variant="body1">
                                    {totalResults >= 0
                                        ? totalResults === 0
                                            ? `No results for "${userQuery}". Try different keywords or clear filters.`
                                            : `${totalResults} result${totalResults !== 1 ? "s" : ""} for "${userQuery}" in ${queryTimeText}`
                                        : ""}
                                </Typography>
                                {allResults.length > 0 && (
                                    <Button
                                        size="small"
                                        variant="outlined"
                                        startIcon={<FileDownloadIcon />}
                                        onClick={() => {
                                            const headers = displayColumns.map((c) => c.name);
                                            const escape = (v) => {
                                                const s = v == null ? "" : String(v);
                                                return s.includes(",") || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
                                            };
                                            const rows = allResults.map((r) => displayColumns.map((c) => escape(r[c.id])).join(","));
                                            const csv = [headers.join(","), ...rows].join("\n");
                                            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement("a");
                                            a.href = url;
                                            a.download = `asrs-results-${userQuery.replace(/\s+/g, "-").slice(0, 30)}.csv`;
                                            a.click();
                                            URL.revokeObjectURL(url);
                                        }}
                                    >
                                        Export CSV
                                    </Button>
                                )}
                            </Box>
                            <DataTable
                                value={searchResults}
                                scrollable
                                showBoxlines
                                stripedRows
                                style={{ width: '100%', maxWidth: '100%' }}
                                lazy={true}
                                paginator={true}
                                rows={pageLength}
                                totalRecords={totalResults}
                                onPage={onPage}
                                first={currentPage * pageLength}
                                emptyMessage="No Records Found"
                                paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
                                currentPageReportTemplate="Showing {first} to {last} of {totalRecords} entries"
                            >
                                {/* Relevance feedback column */}
                                <Column
                                    key="feedback"
                                    header="Relevant?"
                                    body={(record) => {
                                        const docId = record.acn_num_ACN ?? record.parent_doc_id ?? "";
                                        const sent = feedbackSent[docId];
                                        const handleFeedback = (relevant) => {
                                            if (!userQuery || !docId) return;
                                            submitFeedback(userQuery, String(docId), relevant)
                                                .then(() => setFeedbackSent((prev) => ({ ...prev, [docId]: relevant })))
                                                .catch(() => {});
                                        };
                                        return (
                                            <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                                                {sent === true && <Typography variant="caption" color="success.main">Thanks</Typography>}
                                                {sent === false && <Typography variant="caption" color="text.secondary">Recorded</Typography>}
                                                {sent === undefined && (
                                                    <>
                                                        <Tooltip title="Relevant">
                                                            <IconButton size="small" onClick={() => handleFeedback(true)} aria-label="Relevant">
                                                                <ThumbUpOffAltIcon fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                        <Tooltip title="Not relevant">
                                                            <IconButton size="small" onClick={() => handleFeedback(false)} aria-label="Not relevant">
                                                                <ThumbDownOffAltIcon fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </>
                                                )}
                                            </Box>
                                        );
                                    }}
                                    style={{ minWidth: "100px" }}
                                />
                                {/* Display selected columns */}
                                {displayColumns.map((col, i) => {
                                    const id = col["id"]
                                    const colName = col["name"]

                                    return <Column
                                        key = {i}
                                        field = {id}
                                        header = {colName}
                                        style = {{
                                            minWidth: "130px",
                                            wordWrap: "break-word"
                                        }}
                                        body = {(record) => {
                                            // Format table cells
                                            return <Box
                                                sx = {{
                                                    minHeight: '60px',
                                                    maxHeight: '200px',
                                                    overflowY: 'auto',
                                                    verticalAlign: 'top',
                                                    pt: 0.5,
                                                    whiteSpace: 'normal',
                                                    wordWrap: 'break-word',
                                                    lineHeight: 1.4,
                                                    fontSize: '0.875rem',
                                                    '&::-webkit-scrollbar': { width: '6px' },
                                                    '&::-webkit-scrollbar-track': { 
                                                        background: '#f1f1f1', 
                                                        borderRadius: '3px' 
                                                    },
                                                    '&::-webkit-scrollbar-thumb': { 
                                                        background: '#c1c1c1', 
                                                        borderRadius: '3px' 
                                                    },
                                                    '&::-webkit-scrollbar-thumb:hover': { 
                                                        background: '#a1a1a1' 
                                                    }
                                                }}
                                            >
                                                { id === "Report 1_Narrative"
                                                    ? <NarrativeWithHighlightAndChunk narrative={record[id]} snippet={record.snippet} query={userQuery} />
                                                    : record[id] }
                                            </Box>
                                        }}
                                    />
                                })}
                            </DataTable>
                        </Box>
                    )}
                </Grid>
            </Grid>
        </Box>
    </>
}