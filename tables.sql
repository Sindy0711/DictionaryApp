-- Bảng NguoiDung
CREATE TABLE NguoiDung (
    ma_nguoi_dung SERIAL PRIMARY KEY,
    ten_dang_nhap VARCHAR(255) UNIQUE NOT NULL,
    ten_nguoi_dung VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    mat_khau VARCHAR(255) NOT NULL,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng TuVung
CREATE TABLE TuVung (
    ma_tu_vung SERIAL PRIMARY KEY,
    tu VARCHAR(255) NOT NULL,
    phienam VARCHAR,
    nghia TEXT NOT NULL,
    motachung TEXT,
    vi_du TEXT,
);

-- Bảng TrangTuVung
CREATE TABLE TrangTuVung (
    ma_trang SERIAL PRIMARY KEY,
    ten_trang VARCHAR(255),
    icon TEXT,
    mo_ta TEXT,
    ma_nguoi_dung INT,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung)
);

-- Bảng CauHoi
CREATE TABLE CauHoi (
    ma_cau_hoi SERIAL PRIMARY KEY,
    cau_hoi TEXT NOT NULL,
    lua_chon_a TEXT NOT NULL,
    lua_chon_b TEXT NOT NULL,
    lua_chon_c TEXT NOT NULL,
    lua_chon_d TEXT NOT NULL,
    dap_an TEXT NOT NULL
    FOREIGN KEY (ma_trang) REFERENCES TrangTuVung(ma_trang)
);

-- Bảng TienDoHocTu
CREATE TABLE TienDoHocTu (
    ma_trang INT,
    ma_nguoi_dung INT,
    ma_tu_vung INT,
    diem INT NOT NULL,
    ngay_hoc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lan_cuoi_hoc TIMESTAMP, 
    PRIMARY KEY (ma_trang, ma_nguoi_dung, ma_tu_vung),
    FOREIGN KEY (ma_nguoi_dung) REFERENCES NguoiDung(ma_nguoi_dung),
    FOREIGN KEY (ma_tu_vung) REFERENCES TuVung(ma_tu_vung),
    FOREIGN KEY (ma_trang) REFERENCES TrangTuVung(ma_trang)
);


