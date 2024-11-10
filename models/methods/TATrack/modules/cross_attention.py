import torch
import torch.nn as nn


class CrossAttention(nn.Module):
    def __init__(self, dim, num_heads=8, qkv_bias=False, qk_scale=None, attn_drop=0., proj_drop=0.,
                 attn_pos_encoding_only=False):
        super(CrossAttention, self).__init__()
        assert dim % num_heads == 0, f"dim {dim} should be divided by num_heads {num_heads}."

        self.dim = dim
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = qk_scale or head_dim ** -0.5

        if attn_pos_encoding_only:
            self.q = nn.Linear(dim, dim, bias=qkv_bias)
            self.kv = nn.Linear(dim, 2 * dim, bias=qkv_bias)
        else:
            self.q = nn.Linear(dim, dim, bias=qkv_bias)
            self.k = nn.Linear(dim, dim, bias=qkv_bias)
            self.v = nn.Linear(dim, dim, bias=qkv_bias)
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(proj_drop)

        self.attn_pos_encoding_only = attn_pos_encoding_only

    def forward(self, q, kv, q_ape, k_ape, attn_pos):
       
        B, q_N, C = q.shape
        kv_N = kv.shape[1]

        if self.attn_pos_encoding_only: #是否只使用位置编码来计算注意力
            assert q_ape is None and k_ape is None
            q = self.q(q).reshape(B, q_N, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)
            kv = self.kv(kv).reshape(B, kv_N, 2, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
            k, v = kv[0], kv[1]
        else:   #查询和键的绝对位置编码（q_ape 和 k_ape）会被加到 q 和 kv 上
            q = q + q_ape if q_ape is not None else q
            q = self.q(q).reshape(B, q_N, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)
            k = kv + k_ape if k_ape is not None else kv
            k = self.k(k).reshape(B, -1, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)
            v = self.v(kv).reshape(B, -1, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)

        attn = q @ k.transpose(-2, -1)
        attn = attn * self.scale
        if attn_pos is not None:
            attn = attn + attn_pos
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)
        x = attn @ v
        x = x.transpose(1, 2).reshape(B, q_N, C)
        x = self.proj(x)
        x = self.proj_drop(x)

        return x
