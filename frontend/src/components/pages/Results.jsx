import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import { useState } from "react";
import { Box, Grid } from "@mui/material";
import { MetadataFilters, SearchBar } from "../common";

export const Results = () => {
    // Binary if currently waiting on API call
    const [loading, setLoading] = useState(false);
    // Store search results
    const [searchResults, setSearchResults] = useState([]);
    // Total number of results for search
    const [totalResults, setTotalResults] = useState(-1);
    // Primereact table parameters
    const [currentPage, setCurrentPage] = useState(1);
    const [pageLength, setPageLength] = useState(10);

    // Function to submit a new search query
    const onSubmit = () => {

    }

    // Function to collect a new page of results from API
    const onPage = () => {

    }

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
                    backgroundColor: '#f8f9fa'
                }}
            >
                <Grid size = {9}>
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
                        />
                    </Box>
                    
                </Grid>
                <Grid 
                    size = {3}
                    
                >
                    <Box
                        sx={{
                            float: "left"
                        }}
                    >
                        <MetadataFilters
                            disabled={loading}
                            
                        />
                    </Box>
                </Grid>
                <Grid
                    size={12}
                >
                    {loading && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: { xs: 3, sm: "50px" }, width: '100%' }}>
                            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
                                <div className="spinner-border" style={{ width: "5rem", height: "5rem" }} role="status">
                                    <span className="sr-only"></span>
                                </div>
                            </div>
                        </Box>
                    )}

                    {!loading && (
                        <Box sx={{ 
                            width: '100%',
                            maxWidth: '95dvw',
                            display: 'flex',
                            justifyContent: 'center'
                        }}>
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
                                resizableColumns
                                columnResizeMode="expand"
                            >
                                {/* Choose columns to display */}
                                <Column/>
                            </DataTable>
                        </Box>
                    )}
                </Grid>
            </Grid>
            
            
        </Box>
    </>
}