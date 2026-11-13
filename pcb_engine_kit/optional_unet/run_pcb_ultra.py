import sys
import cv2
import numpy as np
import torch
import torch.nn as nn
from skimage.filters import frangi

class ResBlock(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_c, out_c, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.SiLU(inplace=True),
            nn.Conv2d(out_c, out_c, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_c)
        )
        self.shortcut = nn.Conv2d(in_c, out_c, 1, bias=False) if in_c != out_c else nn.Identity()
        self.act = nn.SiLU(inplace=True)
    def forward(self, x):
        return self.act(self.conv(x) + self.shortcut(x))

class AttentionGate(nn.Module):
    def __init__(self, f_g, f_l, f_int):
        super().__init__()
        self.W_g = nn.Sequential(nn.Conv2d(f_g, f_int, 1, bias=False), nn.BatchNorm2d(f_int))
        self.W_x = nn.Sequential(nn.Conv2d(f_l, f_int, 1, bias=False), nn.BatchNorm2d(f_int))
        self.psi = nn.Sequential(nn.Conv2d(f_int, 1, 1, bias=False), nn.BatchNorm2d(1), nn.Sigmoid())
        self.relu = nn.ReLU(inplace=True)
    def forward(self, g, x):
        psi = self.relu(self.W_g(g) + self.W_x(x))
        return x * self.psi(psi)

class ResAttentionUNet(nn.Module):
    def __init__(self, in_channels=5):
        super().__init__()
        self.e1 = ResBlock(in_channels, 32)
        self.e2 = ResBlock(32, 64)
        self.e3 = ResBlock(64, 128)
        self.e4 = ResBlock(128, 256)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = ResBlock(256, 512)
        self.u4 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.att4 = AttentionGate(256, 256, 128)
        self.d4 = ResBlock(512, 256)
        self.u3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.att3 = AttentionGate(128, 128, 64)
        self.d3 = ResBlock(256, 128)
        self.u2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.att2 = AttentionGate(64, 64, 32)
        self.d2 = ResBlock(128, 64)
        self.u1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.att1 = AttentionGate(32, 32, 16)
        self.d1 = ResBlock(64, 32)
        self.out = nn.Conv2d(32, 1, 1)
    def forward(self, x):
        s1 = self.e1(x)
        s2 = self.e2(self.pool(s1))
        s3 = self.e3(self.pool(s2))
        s4 = self.e4(self.pool(s3))
        b = self.bottleneck(self.pool(s4))
        up4 = self.u4(b)
        x = self.d4(torch.cat([up4, self.att4(up4, s4)], dim=1))
        up3 = self.u3(x)
        x = self.d3(torch.cat([up3, self.att3(up3, s3)], dim=1))
        up2 = self.u2(x)
        x = self.d2(torch.cat([up2, self.att2(up2, s2)], dim=1))
        up1 = self.u1(x)
        x = self.d1(torch.cat([up1, self.att1(up1, s1)], dim=1))
        return self.out(x)

def compute_5channel_features(img_bgr, target_size=320):
    img_up = cv2.resize(img_bgr, (target_size, target_size), interpolation=cv2.INTER_CUBIC)
    blur = cv2.GaussianBlur(img_up, (0, 0), 1.8)
    sharp = cv2.addWeighted(img_up, 1.7, blur, -0.7, 0)
    lab = cv2.cvtColor(sharp, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    cl = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(8, 8)).apply(l)
    clean_l = cv2.bilateralFilter(cl, 5, 50, 50)
    valid_mask = ((clean_l > 35) & (clean_l < 222)).astype(np.uint8)
    th_thin = cv2.morphologyEx(clean_l, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    th_wide = cv2.morphologyEx(clean_l, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    tophat_ch = cv2.bitwise_and(cv2.addWeighted(th_thin, 0.6, th_wide, 0.6, 0), valid_mask * 255)
    tophat_ch = cv2.normalize(tophat_ch, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    frangi_map = frangi(clean_l.astype(np.float32) / 255.0, sigmas=[1.5, 3.0, 5.0], black_ridges=False)
    frangi_u8 = cv2.normalize(frangi_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    gx = cv2.Scharr(clean_l, cv2.CV_32F, 1, 0)
    gy = cv2.Scharr(clean_l, cv2.CV_32F, 0, 1)
    grad_mag = cv2.normalize(cv2.magnitude(gx, gy), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    hessian_grad_ch = cv2.bitwise_and(cv2.addWeighted(frangi_u8, 1.3, grad_mag, 0.4, 0), valid_mask * 255)
    enhanced_rgb = cv2.cvtColor(cv2.merge([clean_l, a, b]), cv2.COLOR_LAB2RGB)
    return enhanced_rgb, tophat_ch, hessian_grad_ch

def extract_pcb_traces(image_path, weights_path="pcb_ultra_resatt_unet.pth", out_path="extracted_traces_hd.png"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ResAttentionUNet(in_channels=5).to(device)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    orig_h, orig_w = img_bgr.shape[:2]
    enh_rgb, tophat_ch, hess_ch = compute_5channel_features(img_bgr, target_size=320)
    inp_np = np.dstack([enh_rgb, tophat_ch, hess_ch]).astype(np.float32) / 255.0
    x = torch.from_numpy(inp_np).permute(2, 0, 1).unsqueeze(0).to(device)
    with torch.no_grad():
        p1 = torch.sigmoid(model(x))
        p2 = torch.flip(torch.sigmoid(model(torch.flip(x, [3]))), [3])
        p3 = torch.flip(torch.sigmoid(model(torch.flip(x, [2]))), [2])
        prob_map = ((p1 + p2 + p3) / 3.0).cpu().numpy()[0, 0]
    raw_bin = (prob_map > 0.48).astype(np.uint8) * 255
    closed = cv2.morphologyEx(raw_bin, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    clean = np.zeros_like(closed)
    for idx in range(1, num_l):
        if stats[idx, cv2.CC_STAT_AREA] >= 14:
            clean[labels == idx] = 255
    binary_white_board = cv2.bitwise_not(clean)
    final_full_res = cv2.resize(binary_white_board, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(out_path, final_full_res)
    print(f"Successfully saved high-contrast binary trace map to: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        extract_pcb_traces(sys.argv[1])
    else:
        print("Usage: python run_pcb_ultra.py <path_to_pcb_image.jpg>")
