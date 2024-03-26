module VLOA
    #(
        parameter width = 32,
        parameter approxWidth = 8
    )(
        input  [width-1:0] a,
        input  [width-1:0] b,
        input              cin,
        output [width-1:0] s,
        output             cout
    );

    assign {cout, s} = {{1'b0, a[width-1:approxWidth]} + {1'b0, b[width-1:approxWidth]}, a[approxWidth-1:0] | b[approxWidth-1:0]};
endmodule