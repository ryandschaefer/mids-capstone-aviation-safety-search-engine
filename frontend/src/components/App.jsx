import { React, useState, useEffect } from "react";
import "../styles/style.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Search, Results } from "./pages";

export const App = () => {
    return <>
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Search/>}/>
                <Route path="/results" element={<Results/>}/>
            </Routes>
        </BrowserRouter>
    </>
}