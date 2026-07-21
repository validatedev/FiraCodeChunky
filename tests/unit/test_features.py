import io

from fontTools.feaLib.parser import Parser

from fira_code_chunky.features import sanitize_features

# Upstream Fira Code stores character-variant UI labels as `featureNames`
# blocks inside cvXX features. feaLib only accepts `featureNames` in stylistic
# sets (ssXX); cvXX must use `cvParameters { FeatUILabelNameID { ... } }`.
CV_SOURCE = """\
feature cv01 {
featureNames {
  name "alternate lowercase a";
};
# automatic
sub a by a.cv01;
} cv01;

feature ss01 {
featureNames {
  name "stylistic set one";
};
sub a by a.ss01;
} ss01;

feature calt {
sub a by a.ss01;
} calt;
"""


def _parse(text):
    Parser(
        io.StringIO(text),
        glyphNames={"a", "a.cv01", "a.ss01"},
    ).parse()


def test_raw_cv_feature_names_is_rejected_by_fealib():
    try:
        _parse(CV_SOURCE)
    except Exception as error:
        assert "featureNames" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected feaLib to reject cvXX featureNames")


def test_sanitize_rewrites_cv_feature_names_to_cvparameters():
    fixed = sanitize_features(CV_SOURCE)

    assert "cvParameters {" in fixed
    assert "FeatUILabelNameID {" in fixed
    assert 'name "alternate lowercase a";' in fixed
    # ssXX featureNames must be preserved verbatim.
    assert 'featureNames {\n  name "stylistic set one";' in fixed
    _parse(fixed)  # now compiles


def test_sanitize_is_identity_without_cv_features():
    plain = "feature calt {\nsub a by a.ss01;\n} calt;\n"
    assert sanitize_features(plain) == plain


def test_sanitize_handles_empty_text():
    assert sanitize_features("") == ""
