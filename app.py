import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def count_items_in_pdf(pdf_file):
    """Menghitung jumlah item dalam PDF berdasarkan pola nomor urut."""
    item_count = 0
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                matches = re.findall(r'^\d{1,3}\s+000000', text, re.MULTILINE)
                item_count += len(matches)
    return item_count

def extract_tanggal_faktur(pdf_file):
    """Mencari tanggal faktur di dalam PDF."""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                match = re.search(r'\b(\d{2}-\d{2}-\d{4})\b', text)
                if match:
                    return match.group(1)
    return "Tidak ditemukan"

def extract_data_from_pdf(pdf_file):
    data = []
    no_fp, nama_penjual, nama_pembeli = None, None, None
    tanggal_faktur = extract_tanggal_faktur(pdf_file)
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                no_fp_match = re.search(r'Kode dan Nomor Seri Faktur Pajak:\s*(\d+)', text)
                if no_fp_match:
                    no_fp = no_fp_match.group(1)
                
                penjual_match = re.search(r'Nama\s*:\s*([\w\s\-.,&]+)\nAlamat', text)
                if penjual_match:
                    nama_penjual = penjual_match.group(1).strip()
                
                pembeli_match = re.search(r'Pembeli Barang Kena Pajak/Penerima Jasa Kena Pajak:\s*Nama\s*:\s*([\w\s\-.,&]+)\nAlamat', text)
                if pembeli_match:
                    nama_pembeli = pembeli_match.group(1).strip()
            
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 4 and row[0].isdigit():
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        
                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                        if harga_qty_info:
                            harga = int(float(harga_qty_info.group(1).replace('.', '').replace(',', '.')))
                            qty = int(float(harga_qty_info.group(2).replace('.', '').replace(',', '.')))
                            unit = harga_qty_info.group(3)
                        else:
                            harga, qty, unit = 0, 0, "Unknown"
                        
                        total = harga * qty
                        dpp = total / 1.11
                        ppn = total - dpp
                        
                        item = [
                            no_fp if no_fp else "Tidak ditemukan", 
                            nama_penjual if nama_penjual else "Tidak ditemukan", 
                            nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                            nama_barang, harga, unit, qty, total, dpp, ppn, 
                            tanggal_faktur  
                        ]
                        data.append(item)
    return data
