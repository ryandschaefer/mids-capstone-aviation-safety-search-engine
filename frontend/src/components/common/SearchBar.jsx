import { useState } from "react";
import { InputAdornment, TextField } from "@mui/material";
import { Search as SearchIcon } from "@mui/icons-material";

export const SearchBar = ({ disabled, onSubmit }) => {
    const [userQuery, setUserQuery] = useState("");

    const onEnter = (event) => {
        if (event.key == "Enter") {
            onSubmit(userQuery);
        }
    }

    return <>
        <TextField
            sx={{ 
                width: { xs: "100%" },
                backgroundColor: 'white'
            }}
            id="searchTerm"
            placeholder="Search ASRS..."
            variant="outlined"
            value={userQuery}
            onChange={event => { setUserQuery(event.target.value) }}
            onKeyDown={onEnter}
            disabled={disabled}
            InputProps={{
                startAdornment: (
                    <InputAdornment position="start">
                        <SearchIcon color="action" />
                    </InputAdornment>
                ),
            }}
        />
    </>
}